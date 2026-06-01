"""
视频生成异步任务
"""
from datetime import datetime
from celery import Task
from sqlalchemy.orm import Session
import asyncio
import uuid
import re

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

        # 先确定视频供应商，决定是否需要语音步骤
        digital_human_client = asyncio.run(ClientFactory.create_client(db, user_id, "digital_human"))
        digital_provider = digital_human_client.get_provider_name()
        requires_tts = digital_human_client.requires_tts_audio()

        audio_url = None
        if requires_tts:
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
            _add_log(db, project.id, "info", "audio_sync_mode", f"检测到 {digital_provider} 音画同步渠道，跳过语音合成步骤")

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

        storyboard_urls, storyboard_context = _load_storyboard_video_inputs(db, project)
        reference_urls, reference_context = _load_reference_image_video_inputs(db, project)
        prompt_only_video = bool(project.config.get("prompt_only_video")) and not reference_urls and not storyboard_urls
        primary_image_url = None if prompt_only_video else avatar.file_url
        video_image_urls = reference_urls or storyboard_urls
        prompt_context = "\n\n".join([part for part in [reference_context, storyboard_context] if part])

        video_prompt = project.config.get("performance_prompt", "")
        if not requires_tts:
            video_prompt = _compose_audio_sync_video_prompt(
                script_content=project.script_content or "",
                performance_prompt=project.config.get("performance_prompt", ""),
                storyboard_context=prompt_context,
                language=project.config.get("language", "zh"),
                prompt_mode=project.config.get("prompt_mode", "script"),
            )
            _add_log(db, project.id, "info", "audio_sync_prompt", f"音画同步最终提示词: {video_prompt[:300]}")

        resolution_value = None if not requires_tts else project.config.get("resolution", "480p")

        video_task_id = asyncio.run(digital_human_client.create_video_task(
            audio_url=audio_url,
            image_url=primary_image_url,
            prompt=video_prompt,
            resolution=resolution_value,
            seed=project.config.get("seed", -1),
            storyboard_image_urls=video_image_urls if digital_human_client.supports_storyboard_images() else [],
            storyboard_mode=project.config.get("storyboard_mode", "none"),
            negative_prompt=_compose_storyboard_negative_prompt(project.config.get("language", "zh")),
        ))

        project.video_task_id = video_task_id
        db.commit()

        # 等待视频生成完成
        video_url = asyncio.run(digital_human_client.wait_for_completion(
            task_id=video_task_id,
            max_wait_seconds=int(digital_human_client.get_config_value("timeout", 1200))
        ))

        project.video_url = video_url
        project.progress = 90
        project.error_message = None
        project.error_code = None
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
            will_retry = self.request.retries < self.max_retries
            project.error_message = str(e)
            project.retry_count = self.request.retries + 1
            if will_retry:
                project.status = ProjectStatus.GENERATING_VIDEO
                project.current_step = "生成遇到临时错误，正在重试..."
                project.progress = max(project.progress or 0, 50)
            else:
                project.status = ProjectStatus.FAILED
                project.current_step = "生成失败"
                project.progress = 0
            db.commit()

            _add_log(
                db,
                project.id,
                "warning" if will_retry else "error",
                "retry_scheduled" if will_retry else "failed",
                f"{'任务失败，准备重试' if will_retry else '任务失败'}: {str(e)}"
            )

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


def _load_storyboard_video_inputs(db: Session, project: Project) -> tuple[list[str], str]:
    """读取可作为视频输入的分镜图片，以及只作为导演提示的分镜文本。"""
    asset_ids = project.config.get("storyboard_asset_ids") or []
    if not asset_ids:
        return [], ""
    assets = db.query(Asset).filter(
        Asset.id.in_(asset_ids),
        Asset.type == "storyboard"
    ).all()
    by_id = {str(asset.id): asset for asset in assets}
    urls = []
    contexts = []
    for asset_id in asset_ids:
        asset = by_id.get(str(asset_id))
        if not asset:
            continue
        metadata = asset.meta_data or {}
        is_storyboard_sheet = metadata.get("layout") == "3x3_grid" or metadata.get("panel_count") == 9
        if is_storyboard_sheet:
            context = _extract_director_context(asset.generation_prompt or asset.description or "")
            if context:
                contexts.append(context)
            continue
        context = _format_shot_context(asset, len(contexts) + 1)
        if context:
            contexts.append(context)
        if asset.file_url:
            urls.append(asset.file_url)
    return urls, "\n\n".join(contexts)


def _load_reference_image_video_inputs(db: Session, project: Project) -> tuple[list[str], str]:
    """读取简单创作的多图参考，按用户选择顺序传给视频模型。"""
    asset_ids = project.config.get("reference_image_asset_ids") or []
    if not asset_ids:
        return [], ""
    assets = db.query(Asset).filter(
        Asset.id.in_(asset_ids),
        Asset.type == "avatar"
    ).all()
    by_id = {str(asset.id): asset for asset in assets}
    urls = []
    labels = []
    for index, asset_id in enumerate(asset_ids, start=1):
        asset = by_id.get(str(asset_id))
        if not asset or not asset.file_url:
            continue
        urls.append(asset.file_url)
        labels.append(f"image {index} = 图片{index}（{asset.title}）")

    if not urls:
        return [], ""

    context = (
        "多图参考映射：用户上传/选择的参考图会按顺序传入视频模型，"
        f"{'，'.join(labels)}。请严格按照用户提示词中“图片1/图片2/图片3”等引用理解每张图片，"
        "保持参考图中的人物、物体、服装、材质和场景身份一致；不要把多张图拼成网格或分屏。"
    )
    return urls, context


def _compose_audio_sync_video_prompt(
    script_content: str,
    performance_prompt: str,
    storyboard_context: str = "",
    language: str = "zh",
    prompt_mode: str = "script",
) -> str:
    """
    将“视频提示词 + 人物口播文案”汇总成音画同步视频最终提示词。
    """
    language = language if language in {"zh", "en"} else "zh"
    parts = []
    video_part = (performance_prompt or "").strip()
    speech_part = (script_content or "").strip()
    prompt_mode = prompt_mode if prompt_mode in {"script", "direct"} else "script"
    spoken_part = _extract_spoken_script(speech_part)
    has_chinese_script = bool(re.search(r"[\u4e00-\u9fff]", spoken_part or speech_part))

    if prompt_mode == "direct":
        if language == "en" and not has_chinese_script:
            if speech_part:
                parts.append(f"Direct video generation prompt from user: {speech_part}")
            if video_part:
                parts.append(f"Additional performance direction: {video_part}")
            parts.append("Use the user's wording as visual/audio direction. If speech is requested, keep the original language and do not translate it.")
            if storyboard_context:
                parts.append(
                    "Reference images are provided in order. Follow image 1, image 2, image 3... according to the user's prompt. "
                    "Create one continuous audio-sync video; do not show a grid, collage, split screen, panel borders, or storyboard sheet. "
                    f"{storyboard_context}"
                )
            fallback = "Create one realistic audio-sync video from the provided images and prompt."
        else:
            if speech_part:
                parts.append(f"用户直接视频生成提示词：{speech_part}")
            if video_part:
                parts.append(f"补充动作/表演提示词：{video_part}")
            parts.append("请把用户原文当作视频生成提示词执行；如果用户要求口播或对话，必须保持原语言，不要翻译成英文，也不要自行添加英文旁白。")
            if storyboard_context:
                parts.append(
                    "参考图按顺序传入：请根据用户提示词中的 图片1、图片2、图片3 等引用理解多图关系。"
                    "生成一个连续的音画同步视频；不要出现网格、分屏、拼贴、分镜板、黑色分隔线或多画面同时展示。"
                    f"{storyboard_context}"
                )
            fallback = "根据提供的参考图片和文字提示生成一个真实自然的音画同步视频。"

        final_prompt = "\n".join(parts).strip()
        return final_prompt or fallback

    if language == "en" and not has_chinese_script:
        if video_part:
            parts.append(f"Video prompt: {video_part}")
        if speech_part and speech_part != "[DIRECT_AUDIO_MODE]":
            parts.append("Language lock: English voiceover only. Read the spoken script verbatim. Do not translate, rewrite, summarize, or add extra narration.")
            parts.append(f"Spoken script to read verbatim: {spoken_part}")
            if spoken_part != speech_part:
                parts.append(f"Director notes for visuals only, never read aloud: {speech_part}")
        if storyboard_context:
            parts.append(
                "Multi-shot storyboard references. Use the provided reference images in order as keyframes: "
                "image 1 = Shot 1, image 2 = Shot 2, image 3 = Shot 3. Create one continuous video with natural camera transitions between shots. "
                "Do not show a grid, collage, split screen, panel borders, or storyboard sheet. "
                f"{storyboard_context}"
            )
        fallback = "A person faces the camera and speaks naturally. Keep the frame stable, clear, and realistic."
    else:
        if video_part:
            parts.append(f"视频提示词：{video_part}")
        if speech_part and speech_part != "[DIRECT_AUDIO_MODE]":
            parts.append("语言锁定：必须使用中文普通话口播。不要翻译成英文，不要改写成英文，不要添加英文旁白。")
            parts.append(f"必须逐字口播的中文台词：{spoken_part}")
            if spoken_part != speech_part:
                parts.append(f"导演脚本参考：以下内容只用于画面节奏和动作设计，不要把秒数、画面说明、口播标签念出来：{speech_part}")
        if storyboard_context:
            parts.append(
                "多镜头分镜参考：请按提供的参考图顺序使用 keyframes，多图顺序为 image 1 = Shot 1，image 2 = Shot 2，image 3 = Shot 3。"
                "生成一个连续视频，镜头之间自然转场；不要出现网格、九宫格、分栏、黑色分隔线、拼贴画面或分镜板布局。"
                f"{storyboard_context}"
            )
        fallback = "人物正对镜头自然说话，画面稳定清晰。"

    final_prompt = "\n".join(parts).strip()
    if not final_prompt:
        final_prompt = fallback
    return final_prompt


def _extract_spoken_script(script_content: str) -> str:
    """
    从“画面 + 口播”格式脚本里提取真正要念的台词。
    没有口播标签时，保持原文，避免误删用户直接输入的脚本。
    """
    text = (script_content or "").strip()
    if not text:
        return ""

    spoken_lines = []
    for line in re.split(r"[\r\n]+", text):
        item = line.strip()
        if not item:
            continue
        match = re.match(r"^(?:口播|旁白|台词|对白|人物说话内容|spoken script|voiceover)\s*[：:]\s*(.+)$", item, flags=re.I)
        if match:
            spoken = match.group(1).strip()
            spoken = spoken.strip("“”\"'「」")
            if spoken:
                spoken_lines.append(spoken)

    if spoken_lines:
        return "\n".join(spoken_lines)
    return text


def _compose_storyboard_negative_prompt(language: str = "zh") -> str:
    language = language if language in {"zh", "en"} else "zh"
    if language == "en":
        return (
            "storyboard sheet, contact sheet, grid layout, split screen, multiple panels, black borders, "
            "collage, social app UI, subtitles, watermark, random text"
        )
    return "九宫格分镜图，分镜板，网格布局，分屏，多格画面，黑色分隔线，拼贴，社交软件界面，字幕，水印，随机文字"


def _extract_director_context(storyboard_prompt: str) -> str:
    """
    从分镜板生成提示词中只提取镜头节点，避免把“生成九宫格图片”的指令再喂给视频模型。
    """
    import re

    text = (storyboard_prompt or "").strip()
    if not text:
        return ""

    zh_match = re.search(r"九个分镜节点如下：?\s*(.+?)(?:\n?保持真实|$)", text, flags=re.S)
    if zh_match:
        beats = zh_match.group(1).strip()
        return f"镜头动作顺序参考：\n{beats}"

    en_match = re.search(r"Panel beats:\s*(.+?)(?:\n?Keep a consistent|$)", text, flags=re.S | re.I)
    if en_match:
        beats = en_match.group(1).strip()
        return f"Shot sequence reference:\n{beats}"

    # Fallback: keep it brief and remove the strongest sheet-generation instructions.
    cleaned = re.sub(r"输出必须是.*?(?:。|$)", "", text)
    cleaned = re.sub(r"The output must be.*?(?:\\. |$)", "", cleaned, flags=re.I)
    return cleaned[:800]


def _format_shot_context(asset: Asset, fallback_index: int) -> str:
    metadata = asset.meta_data or {}
    shot_index = metadata.get("scene_index") or fallback_index
    prompt = metadata.get("video_prompt") or metadata.get("shot_prompt") or asset.generation_prompt or asset.description or ""
    if not prompt:
        return ""
    return f"\nShot {shot_index} / image {shot_index}: {prompt}"
