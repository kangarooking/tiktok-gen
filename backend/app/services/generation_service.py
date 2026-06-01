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
from app.core.exceptions import ConfigurationError
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

    async def _get_ai_image_client(self, user_id: UUID, provider: Optional[str] = None):
        """获取AI生图客户端（使用用户配置）"""
        return await ClientFactory.create_client(
            self.db, user_id, "ai_image", provider=provider
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

    @staticmethod
    def _infer_image_ext(content_type: Optional[str], source_url: Optional[str] = None) -> str:
        ct = (content_type or "").split(";")[0].strip().lower()
        mapping = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/webp": "webp",
        }
        if ct in mapping:
            return mapping[ct]
        if source_url:
            path = source_url.split("?")[0]
            ext = os.path.splitext(path)[1].lstrip(".").lower()
            if ext in {"png", "jpg", "jpeg", "webp"}:
                return "jpg" if ext == "jpeg" else ext
        return "png"

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

    async def generate_storyboard(
        self,
        user_id: str,
        script_content: str,
        product_name: Optional[str] = None,
        user_prompt: Optional[str] = None,
        style: str = "电影感 TikTok 商品广告，真实商业摄影风格",
        frame_count: int = 3,
        aspect_ratio: str = "9:16",
        image_provider: Optional[str] = None,
        reference_image_url: Optional[str] = None,
        language: str = "zh",
    ) -> Dict:
        """
        根据用户原始提示词和脚本文案生成多张完整单帧分镜图并保存为 storyboard 资产。
        """
        if not script_content.strip():
            raise ValueError("脚本内容不能为空")

        user_uuid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
        storyboard_id = str(uuid.uuid4())
        image_client = await self._get_ai_image_client(user_uuid, image_provider)
        provider = image_client.get_provider_name()
        size = self._storyboard_size_for_provider(provider, aspect_ratio)
        storyboard_specs = self._build_storyboard_specs(
            script_content=script_content,
            product_name=product_name,
            user_prompt=user_prompt,
            style=style,
            frame_count=frame_count,
            aspect_ratio=aspect_ratio,
            has_reference_image=bool(reference_image_url),
            language=language,
        )

        frames = []
        oss_client = None
        storage_error = None
        try:
            oss_client = await self._get_oss_client(user_uuid)
        except ConfigurationError as exc:
            storage_error = str(exc)

        for index, spec in enumerate(storyboard_specs, start=1):
            image_prompt = spec["image_prompt"]
            video_prompt = spec["video_prompt"]
            reference_images = [reference_image_url] if reference_image_url else None
            try:
                result = await image_client.generate_image_with_metadata(
                    image_prompt,
                    size=size,
                    reference_images=reference_images,
                )
            except TypeError:
                result = await image_client.generate_image_with_metadata(image_prompt, reference_images=reference_images)

            image_url = result["image_url"]
            async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
                response = await client.get(image_url)
                if response.status_code >= 400:
                    raise ValueError(f"下载分镜图片失败 ({response.status_code}): {response.text[:200]}")
                image_bytes = response.content
                content_type = (response.headers.get("content-type") or "image/png").split(";")[0].strip().lower()

            saved_url = image_url
            storage_mode = "provider_url"
            if oss_client:
                ext = self._infer_image_ext(content_type, image_url)
                object_key = f"users/{user_uuid}/storyboards/{storyboard_id}/{index:02d}.{ext}"
                if hasattr(oss_client, "generate_object_key"):
                    try:
                        object_key = oss_client.generate_object_key(str(user_uuid), "storyboards", f".{ext}")
                    except Exception:
                        pass

                saved_url = await oss_client.upload_file(
                    file_data=image_bytes,
                    key=object_key,
                    content_type=content_type,
                )
                storage_mode = "cloud_storage"

            asset = Asset(
                user_id=user_uuid,
                type=AssetType.STORYBOARD,
                title=f"Storyboard Shot {index:02d}",
                description=image_prompt,
                source="ai_generated",
                status="ready",
                is_system=False,
                file_url=saved_url,
                file_size_bytes=len(image_bytes),
                file_mime_type=content_type,
                generation_task_id=result.get("task_id"),
                generation_prompt=image_prompt,
                meta_data={
                    "storyboard_id": storyboard_id,
                    "scene_index": index,
                    "scene_count": len(storyboard_specs),
                    "panel_count": 1,
                    "layout": "single_frame",
                    "shot_prompt": image_prompt,
                    "video_prompt": video_prompt,
                    "shot_type": spec.get("shot_type"),
                    "transition_role": spec.get("transition_role"),
                    "source": "storyboard_generation",
                    "product_name": product_name,
                    "user_prompt": user_prompt,
                    "style": style,
                    "reference_image_url": reference_image_url,
                    "aspect_ratio": aspect_ratio,
                    "language": language if language in {"zh", "en"} else "zh",
                    "size": size,
                    "provider": provider,
                    "model": result.get("model"),
                    "origin_image_url": image_url,
                    "storage_mode": storage_mode,
                    "storage_error": storage_error,
                },
            )
            self.db.add(asset)
            self.db.flush()

            frames.append({
                "asset_id": str(asset.id),
                "scene_index": index,
                "prompt": image_prompt,
                "video_prompt": video_prompt,
                "image_url": saved_url,
            })

        self.db.commit()
        return {"storyboard_id": storyboard_id, "frames": frames}

    @staticmethod
    def _storyboard_size_for_provider(provider: str, aspect_ratio: str) -> str:
        if provider == "apimart_gpt_image2":
            return aspect_ratio or "9:16"
        mapping = {
            "9:16": "1024x1792",
            "16:9": "1792x1024",
            "1:1": "1024x1024",
            "4:5": "1024x1280",
            "5:4": "1280x1024",
        }
        return mapping.get(aspect_ratio or "9:16", "1024x1792")

    @staticmethod
    def _build_storyboard_prompts(
        script_content: str,
        product_name: Optional[str],
        user_prompt: Optional[str],
        style: str,
        frame_count: int,
        aspect_ratio: str,
        has_reference_image: bool = False,
        language: str = "zh",
    ) -> List[str]:
        return [
            spec["image_prompt"]
            for spec in GenerationService._build_storyboard_specs(
                script_content=script_content,
                product_name=product_name,
                user_prompt=user_prompt,
                style=style,
                frame_count=frame_count,
                aspect_ratio=aspect_ratio,
                has_reference_image=has_reference_image,
                language=language,
            )
        ]

    @staticmethod
    def _build_storyboard_specs(
        script_content: str,
        product_name: Optional[str],
        user_prompt: Optional[str],
        style: str,
        frame_count: int,
        aspect_ratio: str,
        has_reference_image: bool = False,
        language: str = "zh",
    ) -> List[Dict[str, str]]:
        import re

        language = language if language in {"zh", "en"} else "zh"
        sentences = [s.strip() for s in re.split(r"[。！？!?；;\n]+", script_content) if s.strip()]
        if not sentences:
            sentences = [script_content.strip()]

        chunks = []
        for i in range(frame_count):
            start = round(i * len(sentences) / frame_count)
            end = round((i + 1) * len(sentences) / frame_count)
            part = "。".join(sentences[start:end] or [sentences[min(i, len(sentences) - 1)]])
            chunks.append(part)

        if language == "en":
            product = f"Product: {product_name}. " if product_name else ""
            style_text = style or "cinematic TikTok product ad"
            base_user_prompt = (user_prompt or "").strip()
            base_direction = base_user_prompt or style_text
            reference_text = (
                "Use the provided reference image as the main character/avatar reference. Preserve the person's identity, face, hairstyle, outfit feeling, and overall visual consistency. "
                if has_reference_image else ""
            )
            shot_plans = [
                {
                    "type": "Opening establishing shot",
                    "visual": "medium-wide environmental composition, the main character plus the key pet/product are clearly visible, strong spatial setup, camera-ready opening frame",
                    "motion": "0-3s: slow push-in or lateral slide, introduce the character, pet/product, and use context; end with a gaze, hand movement, or object movement that can transition into Shot 2",
                    "transition": "match cut through hand movement, gaze direction, or product motion into Shot 2",
                },
                {
                    "type": "Action interaction shot",
                    "visual": "medium or close shot with a noticeably different angle, clear hand interaction, product demo, pet reaction, or expressive body movement",
                    "motion": "3-6s: active demonstration or interaction, more kinetic framing, a clear before/after or emotional beat; end with a whip pan, object move, or body turn",
                    "transition": "use the movement tail to cut smoothly into Shot 3",
                },
                {
                    "type": "Closing conversion shot",
                    "visual": "close-up or hero composition, face, pet/product, and final emotional result are emphasized, polished commercial ending frame",
                    "motion": "6-8s: settle into the final benefit or CTA moment, hold the last pose long enough for a clean ending",
                    "transition": "final hold, no new scene after this",
                },
            ]
            specs = []
            for index, chunk in enumerate(chunks, start=1):
                plan = shot_plans[min(index - 1, len(shot_plans) - 1)]
                image_prompt = (
                    f"{product}Create storyboard shot {index}/{frame_count} as one complete {aspect_ratio} vertical image. "
                    f"{reference_text}"
                    f"User original prompt, preserve every subject and keyword exactly: {base_direction}. "
                    f"Extra visual style: {style_text}. "
                    f"Shot role: {plan['type']}. Composition: {plan['visual']}. "
                    f"Shot {index} action/script beat: {chunk}. "
                    "Make this shot visibly different from the other storyboard shots in camera distance, angle, character pose, action, and foreground/background relationship. "
                    "This must be a single full-frame image, not a collage, not a grid, not a storyboard sheet, no split screen. "
                    "Keep realistic commercial photography, clear subject, consistent character, coherent motion continuity. "
                    "No subtitles, no UI, no watermark, no random text."
                )
                video_prompt = (
                    f"Shot {index} / image {index} ({plan['type']}): {plan['motion']}. "
                    f"Use this visual reference for the shot content. Preserve the original user prompt subjects and keywords: {base_direction}. "
                    f"Script beat: {chunk}. Transition: {plan['transition']}."
                )
                specs.append({
                    "image_prompt": image_prompt,
                    "video_prompt": video_prompt,
                    "shot_type": plan["type"],
                    "transition_role": plan["transition"],
                })
        else:
            product = f"产品：{product_name}。" if product_name else ""
            style_text = style or "电影感 TikTok 商品广告，真实商业摄影风格"
            base_user_prompt = (user_prompt or "").strip()
            base_direction = base_user_prompt or style_text
            reference_text = (
                "请以提供的参考图作为主角/形象参考，保持人物身份、脸部特征、发型、服装气质和整体视觉一致性。"
                if has_reference_image else ""
            )
            shot_plans = [
                {
                    "type": "开场建立镜头",
                    "visual": "中远景或环境建立构图，主角、宠物/产品和使用场景同时清晰入画，用空间关系建立第一眼记忆点",
                    "motion": "0-3 秒：镜头缓慢推近或轻微横移，交代主角、宠物/产品和场景，结尾保留手部动作、视线方向或产品移动，方便转到第二镜头",
                    "transition": "用手部动作、视线方向或产品移动做 match cut 转到 Shot 2",
                },
                {
                    "type": "动作互动镜头",
                    "visual": "中景或近景，角度明显不同，突出主角与宠物/产品的互动、演示动作、表情变化或关键卖点",
                    "motion": "3-6 秒：进入更强动作节奏，完成互动、演示或情绪变化；结尾使用转身、挥手、移动产品或快速横移形成转场点",
                    "transition": "顺着动作尾端自然切到 Shot 3",
                },
                {
                    "type": "收束转化镜头",
                    "visual": "近景或英雄镜头，突出脸部情绪、宠物/产品和最终结果，画面更干净、更像广告收尾",
                    "motion": "6-8 秒：落到最终利益点或 CTA，动作变稳，最后保持一个可停留的结束姿态",
                    "transition": "最终定格收束，不再切新场景",
                },
            ]
            specs = []
            for index, chunk in enumerate(chunks, start=1):
                plan = shot_plans[min(index - 1, len(shot_plans) - 1)]
                image_prompt = (
                    f"{product}请生成第 {index}/{frame_count} 张 TikTok 营销短视频分镜图，画幅为 {aspect_ratio} 竖版。"
                    f"{reference_text}"
                    f"用户原始提示词如下，必须完整保留其中的主体、物体、宠物、动作和关键词：{base_direction}。"
                    f"额外视觉风格：{style_text}。"
                    f"镜头定位：{plan['type']}。构图要求：{plan['visual']}。"
                    f"第 {index} 个镜头动作/脚本节点：{chunk}。"
                    "这一张必须和其他分镜在景别、机位、主角姿态、动作和前后景关系上有明显差异，方便视频直接转场；"
                    "输出必须是一张完整的单镜头画面，不要九宫格、不要分镜板、不要拼贴、不要分屏、不要多个小画面；"
                    "保持真实商业摄影质感、自然光影、主体清晰、主角一致、动作具有连续性；"
                    "不要字幕、不要 UI、不要水印、不要随机文字。"
                )
                video_prompt = (
                    f"Shot {index} / image {index}（{plan['type']}）：{plan['motion']}。"
                    f"请以该分镜图作为这一镜头的视觉参考，保留用户原始提示词里的主体和关键词：{base_direction}。"
                    f"脚本节点：{chunk}。转场方式：{plan['transition']}。"
                )
                specs.append({
                    "image_prompt": image_prompt,
                    "video_prompt": video_prompt,
                    "shot_type": plan["type"],
                    "transition_role": plan["transition"],
                })
        return specs

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
