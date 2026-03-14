"""
项目业务逻辑
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from typing import Dict, List, Optional

from app.models.project import Project, ProjectLog
from app.models.asset import Asset
from app.core.constants import ProjectStatus
from app.tasks.video_generation import start_video_generation_task
from app.integrations.client_factory import ClientFactory


class ProjectService:
    """项目服务"""

    def __init__(self, db: Session):
        self.db = db

    async def get_projects(
        self,
        user_id: str,
        status: str = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict:
        """
        获取项目列表

        Args:
            user_id: 用户ID
            status: 状态筛选
            page: 页码
            page_size: 每页数量

        Returns:
            项目列表和分页信息
        """
        query = self.db.query(Project).filter(Project.user_id == user_id)

        if status:
            query = query.filter(Project.status == status)

        # 分页
        total = query.count()
        projects = query.order_by(
            Project.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "list": [self._serialize_project(p) for p in projects],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        }

    async def get_project(self, project_id: str, user_id: str) -> Dict:
        """
        获取项目详情

        Args:
            project_id: 项目ID
            user_id: 用户ID

        Returns:
            项目详情

        Raises:
            ValueError: 项目不存在或无权访问
        """
        project = self.db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id
        ).first()

        if not project:
            raise ValueError("项目不存在")

        return self._serialize_project(project)

    async def create_project(
        self,
        user_id: str,
        title: str,
        avatar_id: str,
        voice_id: str,
        script_id: str = None,
        script_content: str = None,
        emotion: str = "professional",
        emotion_mode: str = "preset",
        emotion_vector: Optional[List[float]] = None,
        emotion_text: Optional[str] = None,
        emotion_alpha: Optional[float] = None,
        emotion_audio_asset_id: Optional[str] = None,
        performance_prompt: str = "",
        resolution: str = "480p",
        use_voice_audio_directly: bool = False
    ) -> Dict:
        """
        创建视频生成项目

        Args:
            user_id: 用户ID
            title: 项目标题
            avatar_id: 形象ID
            voice_id: 音色ID
            script_id: 脚本ID
            script_content: 自定义脚本内容
            emotion: 情感风格
            emotion_mode: 情绪控制模式
            emotion_vector: 8维情感向量
            emotion_text: 情绪文本
            emotion_alpha: 情绪影响因子
            emotion_audio_asset_id: 情绪参考音频资产ID
            performance_prompt: 表演提示词
            resolution: 视频分辨率
            use_voice_audio_directly: 是否直接使用音色音频文件

        Returns:
            创建的项目信息

        Raises:
            ValueError: 参数验证失败
        """
        # 验证资产存在且可访问
        avatar = self._get_accessible_asset(avatar_id, user_id, "avatar")
        voice = self._get_accessible_asset(voice_id, user_id, "voice")
        final_script_content = script_content

        # 如果直接使用音色音频，验证音色有 file_url
        if use_voice_audio_directly:
            if not voice.file_url:
                raise ValueError("所选音色没有音频文件，无法直接使用")
        else:
            # TTS 模式需要验证脚本
            if script_id:
                script = self._get_accessible_asset(script_id, user_id, "script")
                final_script_content = script.content

            if not final_script_content:
                raise ValueError("脚本内容不能为空")

            if emotion_mode == "audio_ref":
                if not emotion_audio_asset_id:
                    raise ValueError("请选择情绪参考音频")
                self._get_accessible_asset(emotion_audio_asset_id, user_id, "voice")

        # 创建项目
        project = Project(
            user_id=user_id,
            title=title or "未命名项目",
            status=ProjectStatus.PENDING,
            progress=0,
            avatar_id=avatar_id,
            voice_id=voice_id,
            script_id=script_id,
            script_content=final_script_content if not use_voice_audio_directly else "[DIRECT_AUDIO_MODE]",
            config={
                "emotion": emotion,
                "emotion_mode": emotion_mode,
                "emotion_vector": emotion_vector,
                "emotion_text": emotion_text,
                "emotion_alpha": emotion_alpha,
                "emotion_audio_asset_id": emotion_audio_asset_id,
                "performance_prompt": performance_prompt,
                "resolution": resolution,
                "seed": -1,
                "use_voice_audio_directly": use_voice_audio_directly
            }
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)

        # 记录日志
        self._add_log(project.id, "info", "project_created", "项目创建成功")

        # 触发异步视频生成任务
        start_video_generation_task.delay(str(project.id))

        return self._serialize_project(project)

    async def get_project_status(
        self,
        project_id: str,
        user_id: str
    ) -> Dict:
        """
        获取项目状态

        Args:
            project_id: 项目ID
            user_id: 用户ID

        Returns:
            项目状态信息
        """
        project = self.db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id
        ).first()

        if not project:
            raise ValueError("项目不存在")

        # 自愈：如果第三方已完成/失败，但本地状态卡在 generating_video，则在查询时自动回填
        await self._reconcile_generating_video_project(project)

        # 定义步骤映射
        steps = [
            {"name": "初始化", "status": "completed"},
            {"name": "生成音频", "status": "pending"},
            {"name": "生成视频", "status": "pending"},
            {"name": "后处理", "status": "pending"}
        ]

        # 根据状态更新步骤
        if project.status == ProjectStatus.GENERATING_AUDIO:
            steps[1]["status"] = "processing"
        elif project.status == ProjectStatus.GENERATING_VIDEO:
            steps[1]["status"] = "completed"
            steps[2]["status"] = "processing"
        elif project.status == ProjectStatus.POST_PROCESSING:
            steps[1]["status"] = "completed"
            steps[2]["status"] = "completed"
            steps[3]["status"] = "processing"
        elif project.status == ProjectStatus.COMPLETED:
            for step in steps:
                step["status"] = "completed"
        elif project.status == ProjectStatus.FAILED:
            for step in steps:
                if step["status"] == "processing":
                    step["status"] = "failed"

        return {
            "id": str(project.id),
            "status": project.status.value if hasattr(project.status, 'value') else project.status,
            "progress": project.progress,
            "current_step": project.current_step or "",
            "steps": steps,
            "error": project.error_message,
            "estimated_remaining_seconds": self._estimate_remaining(project)
        }

    async def _reconcile_generating_video_project(self, project: Project) -> None:
        """对卡在生成中的视频任务进行一次轻量级状态对账。"""
        status = project.status.value if hasattr(project.status, "value") else project.status
        if status != ProjectStatus.GENERATING_VIDEO:
            return
        if not project.video_task_id:
            return

        # 限流：避免前端轮询时每次都打第三方接口
        updated_at = project.updated_at
        if updated_at:
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - updated_at).total_seconds()
            if elapsed < 15:
                return

        try:
            client = await ClientFactory.create_client(self.db, project.user_id, "digital_human")
            if not hasattr(client, "get_task_result"):
                return

            result = await client.get_task_result(project.video_task_id)
            remote_status = str(result.get("status", "")).lower()

            if remote_status in {"succeeded", "success", "completed", "done"}:
                project.status = ProjectStatus.COMPLETED
                project.progress = 100
                project.current_step = "完成"
                project.error_message = None
                if result.get("video_url"):
                    project.video_url = result["video_url"]
                if not project.completed_at:
                    project.completed_at = datetime.utcnow()
                self.db.commit()
                self._add_log(project.id, "info", "reconciled_completed", "检测到第三方已完成，自动回填项目状态")

            elif remote_status in {"failed", "error", "cancelled", "canceled"}:
                project.status = ProjectStatus.FAILED
                project.progress = 0
                project.current_step = "生成失败"
                project.error_message = result.get("error") or "第三方任务失败"
                self.db.commit()
                self._add_log(project.id, "error", "reconciled_failed", f"检测到第三方失败，自动回填失败状态: {project.error_message}")

        except Exception as e:
            # 对账失败不影响主接口返回，仅记录日志用于排查
            self._add_log(project.id, "warning", "reconcile_skipped", f"状态对账失败，稍后重试: {str(e)}")

    async def delete_project(self, project_id: str, user_id: str):
        """
        删除项目

        Args:
            project_id: 项目ID
            user_id: 用户ID

        Raises:
            ValueError: 项目不存在或无权删除
        """
        project = self.db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id
        ).first()

        if not project:
            raise ValueError("项目不存在")

        self.db.delete(project)
        self.db.commit()

    def _get_accessible_asset(
        self,
        asset_id: str,
        user_id: str,
        asset_type: str
    ) -> Asset:
        """获取可访问的资产"""
        asset = self.db.query(Asset).filter(
            Asset.id == asset_id,
            Asset.type == asset_type
        ).first()

        if not asset:
            raise ValueError(f"{asset_type}资产不存在")

        if not asset.is_system and asset.user_id != user_id:
            raise ValueError("无权访问此资产")

        return asset

    def _add_log(
        self,
        project_id: str,
        level: str,
        step: str,
        message: str,
        details: Dict = None
    ):
        """添加项目日志"""
        log = ProjectLog(
            project_id=project_id,
            level=level,
            step=step,
            message=message,
            details=details or {}
        )
        self.db.add(log)
        self.db.commit()

    def _estimate_remaining(self, project: Project) -> int:
        """估算剩余时间（秒）"""
        if project.status == ProjectStatus.COMPLETED:
            return 0
        elif project.status == ProjectStatus.FAILED:
            return 0
        elif project.status == ProjectStatus.PENDING:
            return 120
        elif project.status == ProjectStatus.GENERATING_AUDIO:
            return 60
        elif project.status == ProjectStatus.GENERATING_VIDEO:
            return 300
        elif project.status == ProjectStatus.POST_PROCESSING:
            return 10
        return 60

    def _serialize_project(self, project: Project) -> Dict:
        """序列化项目对象"""
        # 获取关联资产信息
        avatar = self.db.query(Asset).filter(Asset.id == project.avatar_id).first()
        voice = self.db.query(Asset).filter(Asset.id == project.voice_id).first()
        script = None
        if project.script_id:
            script = self.db.query(Asset).filter(Asset.id == project.script_id).first()

        return {
            "id": str(project.id),
            "title": project.title,
            "status": project.status.value if hasattr(project.status, 'value') else project.status,
            "thumbnail_url": project.thumbnail_url,
            "video_url": project.video_url,
            "audio_url": project.audio_url,
            "duration_seconds": float(project.duration_seconds) if project.duration_seconds else None,
            "resolution": project.resolution.value if project.resolution and hasattr(project.resolution, 'value') else project.resolution,
            "progress": project.progress,
            "current_step": project.current_step,
            "error": project.error_message,
            "created_at": project.created_at.isoformat(),
            "completed_at": project.completed_at.isoformat() if project.completed_at else None,
            "assets": {
                "avatar": {
                    "id": str(project.avatar_id),
                    "title": avatar.title if avatar else "",
                    "file_url": avatar.file_url if avatar else None
                },
                "voice": {
                    "id": str(project.voice_id),
                    "title": voice.title if voice else "",
                    "file_url": voice.file_url if voice else None
                },
                "script": {
                    "id": str(project.script_id),
                    "title": script.title if script else "",
                    "content": script.content if script else project.script_content
                } if project.script_id or project.script_content else None
            }
        }
