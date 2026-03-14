"""
视频生成异步任务
"""
from datetime import datetime
from celery import Task
from sqlalchemy.orm import Session
import asyncio
import uuid

from app.tasks import celery_app
from app.database import SessionLocal
from app.models.project import Project, ProjectLog
from app.models.asset import Asset
from app.integrations.client_factory import ClientFactory
from app.core.constants import ProjectStatus


class DatabaseTask(Task):
    """带数据库会话的任务基类"""
    _db = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(bind=True, base=DatabaseTask, max_retries=3)
def start_video_generation_task(self, project_id: str):
    """
    视频生成异步任务
    流程:
    1. 生成音频 (TTS)
    2. 生成视频 (WaveSpeed)
    3. 后处理
    4. 更新项目状态
    """
    db = self.db

    try:
        # 获取项目
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise Exception(f"项目不存在: {project_id}")

        # 获取用户ID用于创建客户端（使用用户配置的API）
        user_id = project.user_id

        # 先确定数字人供应商，决定是否需要语音步骤
        digital_human_client = asyncio.run(ClientFactory.create_client(db, user_id, "digital_human"))
        digital_provider = digital_human_client.get_provider_name()
        use_seedance = (digital_provider == "ark_seedance")

        audio_url = None
        if not use_seedance:
            # 更新状态: 生成音频中
            project.status = ProjectStatus.GENERATING_AUDIO
            project.progress = 10
            project.current_step = "正在生成音频..."
            db.commit()

            _add_log(db, project.id, "info", "tts_start", "开始生成音频")

            # Step 1: 生成音频或直接使用音色音频
            use_voice_audio_directly = project.config.get("use_voice_audio_directly", False)

            if project.voice_id:
                voice = db.query(Asset).filter(Asset.id == project.voice_id).first()
                if voice:
                    if use_voice_audio_directly:
                        # 直接使用音色的音频文件
                        audio_url = voice.file_url
                        _add_log(db, project.id, "info", "audio_direct", f"直接使用音色音频: {audio_url}")
                    else:
                        # TTS 合成 - 使用用户配置的TTS客户端
                        tts_client = asyncio.run(ClientFactory.create_client(db, user_id, "tts"))
                        script_content = project.script_content
                        emotion_audio_url = None
                        emotion_audio_asset_id = project.config.get("emotion_audio_asset_id")
                        if emotion_audio_asset_id:
                            emotion_asset = db.query(Asset).filter(Asset.id == emotion_audio_asset_id).first()
                            if emotion_asset:
                                emotion_audio_url = emotion_asset.file_url
                        provider = tts_client.get_provider_name()
                        if provider == "siliconflow_tts":
                            audio_bytes = asyncio.run(tts_client.synthesize(
                                text=script_content,
                                voice=tts_client.get_config_value("voice"),
                                voice_file_url=voice.file_url,
                                voice_name=voice.title,
                                emotion=project.config.get("emotion", "professional"),
                                emotion_mode=project.config.get("emotion_mode", "preset"),
                                emotion_vector=project.config.get("emotion_vector"),
                                emotion_text=project.config.get("emotion_text"),
                                emotion_alpha=project.config.get("emotion_alpha"),
                                emotion_audio_url=emotion_audio_url,
                            ))
                            oss_client = asyncio.run(ClientFactory.create_client(db, user_id, "cloud_storage"))
                            response_format = str(tts_client.get_config_value("response_format", "mp3")).lower()
                            ext = "wav" if response_format == "pcm" else response_format
                            object_key = f"users/{user_id}/tts/{uuid.uuid4()}.{ext}"
                            if hasattr(oss_client, "generate_object_key"):
                                try:
                                    object_key = oss_client.generate_object_key(str(user_id), "tts", f".{ext}")
                                except Exception:
                                    pass
                            content_type = f"audio/{'mpeg' if ext == 'mp3' else ext}"
                            audio_url = asyncio.run(oss_client.upload_file(
                                file_data=audio_bytes,
                                key=object_key,
                                content_type=content_type,
                            ))
                        else:
                            audio_url = asyncio.run(tts_client.generate_audio(
                                text=script_content,
                                voice_file_url=voice.file_url,
                                emotion=project.config.get("emotion", "professional"),
                                emotion_mode=project.config.get("emotion_mode", "preset"),
                                emotion_vector=project.config.get("emotion_vector"),
                                emotion_text=project.config.get("emotion_text"),
                                emotion_alpha=project.config.get("emotion_alpha"),
                                emotion_audio_url=emotion_audio_url,
                            ))

            if not audio_url:
                raise Exception("音频生成失败")

            project.audio_url = audio_url
            project.tts_task_id = None
            project.progress = 40
            db.commit()

            _add_log(db, project.id, "info", "tts_complete", f"音频生成完成: {audio_url}")
        else:
            _add_log(db, project.id, "info", "seedance_mode", "检测到 Seedance 渠道，跳过语音合成步骤")

        # 更新状态: 生成视频中
        project.status = ProjectStatus.GENERATING_VIDEO
        project.progress = 50
        project.current_step = "正在生成视频..."
        db.commit()

        _add_log(db, project.id, "info", "video_start", "开始生成视频")

        # Step 2: 生成视频 - 使用用户配置的数字人视频客户端
        avatar = db.query(Asset).filter(Asset.id == project.avatar_id).first()
        if not avatar or not avatar.file_url:
            raise Exception("形象素材缺失或无可用图片URL")

        video_prompt = project.config.get("performance_prompt", "")
        if use_seedance:
            video_prompt = _compose_seedance_prompt(
                script_content=project.script_content or "",
                performance_prompt=project.config.get("performance_prompt", ""),
            )
            _add_log(db, project.id, "info", "seedance_prompt", f"Seedance 最终提示词: {video_prompt[:300]}")

        resolution_value = None if use_seedance else project.config.get("resolution", "480p")

        video_task_id = asyncio.run(digital_human_client.create_video_task(
            audio_url=audio_url,
            image_url=avatar.file_url,
            prompt=video_prompt,
            resolution=resolution_value,
            seed=project.config.get("seed", -1)
        ))

        project.video_task_id = video_task_id
        db.commit()

        # 等待视频生成完成
        video_url = asyncio.run(digital_human_client.wait_for_completion(
            task_id=video_task_id,
            max_wait_seconds=600
        ))

        project.video_url = video_url
        project.progress = 90
        db.commit()

        _add_log(db, project.id, "info", "video_complete", f"视频生成完成: {video_url}")

        # Step 3: 后处理
        project.status = ProjectStatus.POST_PROCESSING
        project.current_step = "后处理中..."
        db.commit()

        # TODO: 生成缩略图、计算时长等

        # 完成
        project.status = ProjectStatus.COMPLETED
        project.progress = 100
        project.current_step = "完成"
        project.completed_at = datetime.utcnow()
        db.commit()

        _add_log(db, project.id, "info", "complete", "项目生成完成")

        # TODO: 扣减用户额度

        return {"status": "completed", "video_url": video_url}

    except Exception as e:
        # 错误处理
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = ProjectStatus.FAILED
            project.error_message = str(e)
            project.progress = 0
            db.commit()

            _add_log(db, project.id, "error", "failed", f"任务失败: {str(e)}")

        # 重试逻辑
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)

        raise e


def _add_log(db: Session, project_id: str, level: str, step: str, message: str, details: dict = None):
    """添加项目日志"""
    log = ProjectLog(
        project_id=project_id,
        level=level,
        step=step,
        message=message,
        details=details or {}
    )
    db.add(log)
    db.commit()


def _compose_seedance_prompt(script_content: str, performance_prompt: str) -> str:
    """
    将“视频提示词 + 人物口播文案”汇总成 Seedance 最终提示词。
    """
    parts = []
    video_part = (performance_prompt or "").strip()
    speech_part = (script_content or "").strip()

    if video_part:
        parts.append(f"视频提示词：{video_part}")
    if speech_part and speech_part != "[DIRECT_AUDIO_MODE]":
        parts.append(f"人物说话内容：{speech_part}")

    final_prompt = "\n".join(parts).strip()
    if not final_prompt:
        final_prompt = "人物正对镜头自然说话，画面稳定清晰。"
    return final_prompt
