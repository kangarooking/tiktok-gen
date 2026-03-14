"""
生成业务逻辑
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from uuid import UUID
import uuid
import os
from datetime import datetime
import httpx

from app.models.asset import Asset
from app.core.constants import AssetType
from app.integrations.client_factory import ClientFactory


class GenerationService:
    """生成服务"""

    def __init__(self, db: Session):
        self.db = db

    async def _get_tts_client(self, user_id: UUID):
        """获取TTS客户端（使用用户配置）"""
        return await ClientFactory.create_client(
            self.db, user_id, "tts"
        )

    async def _get_llm_client(self, user_id: UUID):
        """获取LLM客户端（使用用户配置）"""
        return await ClientFactory.create_client(
            self.db, user_id, "llm"
        )

    async def _get_oss_client(self, user_id: UUID):
        """获取云存储客户端（使用用户配置）"""
        return await ClientFactory.create_client(
            self.db, user_id, "cloud_storage"
        )

    async def _upload_tts_audio_bytes(
        self,
        user_id: UUID,
        audio_bytes: bytes,
        response_format: str = "mp3",
    ) -> str:
        """将TTS返回的音频字节上传到云存储并返回公网URL。"""
        oss_client = await self._get_oss_client(user_id)
        ext = (response_format or "mp3").lower()
        if ext == "pcm":
            ext = "wav"
        object_key = f"users/{user_id}/tts/{uuid.uuid4()}.{ext}"
        content_type = f"audio/{'mpeg' if ext == 'mp3' else ext}"

        # 优先使用已有工具函数生成路径（仅OSS客户端实现）
        if hasattr(oss_client, "generate_object_key"):
            try:
                object_key = oss_client.generate_object_key(str(user_id), "tts", f".{ext}")
            except Exception:
                pass

        return await oss_client.upload_file(
            file_data=audio_bytes,
            key=object_key,
            content_type=content_type,
        )

    @staticmethod
    def _infer_audio_ext(content_type: Optional[str], source_url: Optional[str] = None) -> str:
        ct = (content_type or "").split(";")[0].strip().lower()
        mapping = {
            "audio/mpeg": "mp3",
            "audio/mp3": "mp3",
            "audio/wav": "wav",
            "audio/x-wav": "wav",
            "audio/ogg": "ogg",
            "audio/opus": "opus",
            "audio/aac": "aac",
            "audio/mp4": "m4a",
        }
        if ct in mapping:
            return mapping[ct]
        if source_url:
            path = source_url.split("?")[0]
            ext = os.path.splitext(path)[1].lstrip(".").lower()
            if ext:
                return ext
        return "mp3"

    async def generate_audio_preview(
        self,
        user_id: str,
        voice_id: str,
        text: str,
        emotion: str = "professional",
        emotion_mode: str = "preset",
        emotion_vector: Optional[List[float]] = None,
        emotion_text: Optional[str] = None,
        emotion_alpha: Optional[float] = None,
        emotion_audio_asset_id: Optional[str] = None,
    ) -> Dict:
        """
        生成音频预览

        Args:
            user_id: 用户ID
            voice_id: 音色ID
            text: 要合成的文本
            emotion: 情感风格

        Returns:
            音频预览信息

        Raises:
            ValueError: 参数验证失败
        """
        # 获取音色资产
        voice = self.db.query(Asset).filter(
            Asset.id == voice_id,
            Asset.type == "voice"
        ).first()

        if not voice:
            raise ValueError("音色资产不存在")

        if not voice.is_system and voice.user_id != user_id:
            raise ValueError("无权访问此音色")

        emotion_audio_url = None
        if emotion_mode == "audio_ref":
            if not emotion_audio_asset_id:
                raise ValueError("请选择情绪参考音频")
            emotion_asset = self.db.query(Asset).filter(
                Asset.id == emotion_audio_asset_id,
                Asset.type == "voice"
            ).first()
            if not emotion_asset:
                raise ValueError("情绪参考音频不存在")
            if not emotion_asset.is_system and emotion_asset.user_id != user_id:
                raise ValueError("无权访问此情绪参考音频")
            emotion_audio_url = emotion_asset.file_url

        # 获取TTS客户端（使用用户配置）
        tts_client = await self._get_tts_client(user_id if isinstance(user_id, UUID) else UUID(user_id))

        # 调用TTS API生成音频
        provider = tts_client.get_provider_name()
        if provider == "siliconflow_tts":
            audio_bytes = await tts_client.synthesize(
                text=text,
                voice=tts_client.get_config_value("voice"),
                voice_file_url=voice.file_url,
                voice_name=voice.title,
                emotion=emotion,
                emotion_mode=emotion_mode,
                emotion_vector=emotion_vector,
                emotion_text=emotion_text,
                emotion_alpha=emotion_alpha,
                emotion_audio_url=emotion_audio_url,
            )
            audio_url = await self._upload_tts_audio_bytes(
                user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
                audio_bytes=audio_bytes,
                response_format=tts_client.get_config_value("response_format", "mp3"),
            )
        else:
            audio_url = await tts_client.generate_audio(
                text=text,
                voice_file_url=voice.file_url,
                emotion=emotion,
                emotion_mode=emotion_mode,
                emotion_vector=emotion_vector,
                emotion_text=emotion_text,
                emotion_alpha=emotion_alpha,
                emotion_audio_url=emotion_audio_url,
            )

        # 计算预估时长
        estimated_seconds = max(3, len(text) / 7)

        return {
            "audio_url": audio_url,
            "duration_seconds": estimated_seconds,
            "expires_in": 3600  # 1小时后过期
        }

    async def generate_script(
        self,
        user_id: str,
        product_name: str,
        product_description: str,
        target_audience: str = "普通消费者",
        tone: str = "轻松活泼",
        duration_seconds: int = 15
    ) -> Dict:
        """
        AI生成营销脚本

        Args:
            user_id: 用户ID
            product_name: 产品名称
            product_description: 产品描述
            target_audience: 目标受众
            tone: 风格基调
            duration_seconds: 目标时长

        Returns:
            生成的脚本列表
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Generating script for product: {product_name}")

        # 获取LLM客户端（使用用户配置）
        llm_client = await self._get_llm_client(user_id if isinstance(user_id, UUID) else UUID(user_id))

        # 调用LLM生成脚本
        scripts = await llm_client.generate_script(
            product_name=product_name,
            product_description=product_description,
            target_audience=target_audience,
            tone=tone,
            duration_seconds=duration_seconds
        )

        logger.info(f"Generated {len(scripts)} scripts")
        for i, script in enumerate(scripts):
            logger.info(f"Script {i+1}: {script.get('word_count', 0)} words, {len(script.get('content', ''))} chars")

        return {"scripts": scripts}

    async def save_audio_preview(
        self,
        user_id: str,
        audio_url: str,
        title: Optional[str] = None,
        voice_id: Optional[str] = None,
        text: Optional[str] = None,
    ) -> Dict:
        """
        保存预览音频到云存储并写入音色库资产。
        """
        if not audio_url:
            raise ValueError("audio_url 不能为空")

        user_uuid = user_id if isinstance(user_id, UUID) else UUID(user_id)

        # 下载预览音频
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            response = await client.get(audio_url)
            if response.status_code >= 400:
                detail = response.text.strip()
                raise ValueError(f"下载预览音频失败 ({response.status_code}): {detail}")
            audio_bytes = response.content
            content_type = (response.headers.get("content-type") or "audio/mpeg").split(";")[0].strip().lower()

        if not audio_bytes:
            raise ValueError("下载到的音频内容为空")

        # 上传到云存储
        oss_client = await self._get_oss_client(user_uuid)
        ext = self._infer_audio_ext(content_type, audio_url)
        object_key = f"users/{user_uuid}/voices/{uuid.uuid4()}.{ext}"
        if hasattr(oss_client, "generate_object_key"):
            try:
                object_key = oss_client.generate_object_key(str(user_uuid), "voices", f".{ext}")
            except Exception:
                pass

        saved_url = await oss_client.upload_file(
            file_data=audio_bytes,
            key=object_key,
            content_type=content_type,
        )

        final_title = (title or "").strip() or f"TTS Preview {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if len(final_title) > 100:
            final_title = final_title[:100]

        metadata = {
            "source_type": "tts_preview",
            "origin_audio_url": audio_url,
            "voice_id": voice_id,
            "text_excerpt": (text or "")[:200] if text else None,
            "saved_at": datetime.utcnow().isoformat(),
        }

        asset = Asset(
            user_id=user_uuid,
            type=AssetType.VOICE,
            title=final_title,
            source="ai_generated",
            status="ready",
            is_system=False,
            file_url=saved_url,
            file_size_bytes=len(audio_bytes),
            file_mime_type=content_type,
            metadata=metadata,
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)

        return {
            "id": str(asset.id),
            "type": asset.type,
            "title": asset.title,
            "description": asset.description,
            "is_system": asset.is_system,
            "content": asset.content,
            "file_url": asset.file_url,
            "preview_url": asset.preview_url,
            "thumbnail_url": asset.thumbnail_url,
            "metadata": asset.meta_data,
            "status": asset.status,
            "created_at": asset.created_at.isoformat(),
            "tags": [],
        }
