"""
资产业务逻辑
"""
from sqlalchemy.orm import Session, joinedload
from typing import Dict, List, Optional
from fastapi import UploadFile
from uuid import UUID
import uuid
import os
import logging

from app.models.asset import Asset, AssetTag
from app.core.constants import AssetType
from app.core.exceptions import ConfigurationError
from app.integrations.client_factory import ClientFactory
import httpx

logger = logging.getLogger(__name__)


class AssetService:
    """资产服务"""

    def __init__(self, db: Session):
        self.db = db

    async def _get_oss_client(self, user_id: UUID):
        """获取云存储客户端（使用用户配置）"""
        return await ClientFactory.create_client(
            self.db, user_id, "cloud_storage"
        )

    async def _get_ai_image_client(self, user_id: UUID):
        """获取AI生图客户端（使用用户配置）"""
        return await ClientFactory.create_client(
            self.db, user_id, "ai_image"
        )

    async def get_assets(
        self,
        user_id: str,
        asset_type: Optional[str] = None,
        is_system: Optional[bool] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict:
        """
        获取资产列表

        Args:
            user_id: 用户ID
            asset_type: 资产类型筛选
            is_system: 是否系统资产筛选
            keyword: 关键词搜索
            page: 页码
            page_size: 每页数量

        Returns:
            资产列表和分页信息
        """
        query = self.db.query(Asset).options(joinedload(Asset.tags))

        # 筛选条件
        if asset_type:
            query = query.filter(Asset.type == asset_type)

        if is_system is not None:
            query = query.filter(Asset.is_system == is_system)
        else:
            # 默认显示系统资产 + 用户资产
            query = query.filter(
                (Asset.is_system == True) | (Asset.user_id == user_id)
            )

        # 关键词搜索
        if keyword:
            query = query.filter(
                (Asset.title.ilike(f"%{keyword}%")) |
                (Asset.description.ilike(f"%{keyword}%"))
            )

        # 分页
        total = query.count()
        assets = query.order_by(
            Asset.is_system.desc(),
            Asset.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "list": [self._serialize_asset(a) for a in assets],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        }

    async def get_asset(self, asset_id: str, user_id: str) -> Dict:
        """
        获取资产详情

        Args:
            asset_id: 资产ID
            user_id: 用户ID

        Returns:
            资产详情

        Raises:
            ValueError: 资产不存在或无权访问
        """
        asset = self.db.query(Asset).options(joinedload(Asset.tags)).filter(
            Asset.id == asset_id
        ).first()

        if not asset:
            raise ValueError("资产不存在")

        # 检查访问权限
        if not asset.is_system and asset.user_id != user_id:
            raise ValueError("无权访问此资产")

        return self._serialize_asset(asset)

    async def upload_avatar(
        self,
        user_id: str,
        file: UploadFile,
        title: str
    ) -> Dict:
        """
        上传形象图片

        Args:
            user_id: 用户ID
            file: 上传的文件
            title: 资产标题

        Returns:
            创建的资产信息
        """
        # 验证文件
        await self._validate_image_file(file)

        # 读取文件内容
        contents = await file.read()

        # 获取云存储客户端
        oss_client = await self._get_oss_client(user_id if isinstance(user_id, UUID) else UUID(user_id))

        # 生成OSS路径
        file_ext = os.path.splitext(file.filename)[1]
        object_key = oss_client.generate_object_key(
            user_id, "avatars", file_ext
        )

        # 上传到OSS
        file_url = await oss_client.upload_file(
            file_data=contents,
            key=object_key,
            content_type=file.content_type
        )

        # 创建资产记录
        asset = Asset(
            user_id=user_id,
            type=AssetType.AVATAR,
            title=title,
            source="upload",
            status="ready",
            is_system=False,
            file_url=file_url,
            file_size_bytes=len(contents),
            file_mime_type=file.content_type,
            meta_data={"original_filename": file.filename}
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)

        return self._serialize_asset(asset)

    async def generate_avatar(
        self,
        user_id: str,
        title: str,
        prompt: str,
        style: str = None,
        gender: str = None,
        age_range: str = None,
        reference_images: list = None
    ) -> Dict:
        """
        AI生成头像

        Args:
            user_id: 用户ID
            title: 资产标题
            prompt: 头像描述
            style: 图片风格
            gender: 性别
            age_range: 年龄范围
            reference_images: 参考图片文件列表（用于以图生图）

        Returns:
            创建的资产信息
        """
        # 处理参考图片，转换为 base64
        reference_images_base64 = []
        if reference_images:
            import base64
            for img_file in reference_images:
                if img_file and img_file.filename:
                    content = await img_file.read()
                    img_base64 = base64.b64encode(content).decode('utf-8')
                    reference_images_base64.append(img_base64)
                    await img_file.seek(0)  # 重置文件指针

        # 获取AI生图客户端（使用用户配置）
        ai_image_client = await self._get_ai_image_client(user_id if isinstance(user_id, UUID) else UUID(user_id))

        # 调用AI生图
        result = await ai_image_client.generate_avatar_image(
            description=prompt,
            style=style,
            gender=gender,
            age_range=age_range,
            reference_images=reference_images_base64 if reference_images_base64 else None
        )

        image_url = result["image_url"]

        # 下载生成的图片
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(image_url)
            if response.status_code != 200:
                raise Exception(f"Failed to download generated image: {response.status_code}")
            image_data = response.content

        file_url = image_url
        storage_mode = "provider_url"
        storage_error = None
        try:
            # 获取云存储客户端
            oss_client = await self._get_oss_client(user_id if isinstance(user_id, UUID) else UUID(user_id))

            # 生成OSS路径
            file_ext = ".png"
            object_key = oss_client.generate_object_key(
                user_id, "avatars", file_ext
            )

            # 上传到OSS
            file_url = await oss_client.upload_file(
                file_data=image_data,
                key=object_key,
                content_type="image/png"
            )
            storage_mode = "cloud_storage"
        except ConfigurationError as exc:
            storage_error = str(exc)
            logger.warning(
                "Cloud storage is not configured; saving generated avatar provider URL directly: %s",
                storage_error,
            )

        # 创建资产记录
        asset = Asset(
            user_id=user_id,
            type=AssetType.AVATAR,
            title=title,
            source="ai_generated",
            status="ready",
            is_system=False,
            file_url=file_url,
            file_size_bytes=len(image_data),
            file_mime_type="image/png",
            meta_data={
                "prompt": prompt,
                "style": style,
                "gender": gender,
                "age_range": age_range,
                "generation_tokens": result.get("total_tokens", 0),
                "provider": ai_image_client.get_provider_name(),
                "model": result.get("model"),
                "origin_image_url": image_url,
                "storage_mode": storage_mode,
                "storage_error": storage_error,
            }
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)

        return self._serialize_asset(asset)

    async def upload_voice(
        self,
        user_id: str,
        file: UploadFile,
        title: str,
        gender: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict:
        """
        上传音色音频

        Args:
            user_id: 用户ID
            file: 上传的音频文件
            title: 音色名称
            gender: 性别 (male/female)
            tags: 标签列表

        Returns:
            创建的资产信息
        """
        # 验证文件
        await self._validate_audio_file(file)

        # 读取文件内容
        contents = await file.read()

        # 获取云存储客户端
        oss_client = await self._get_oss_client(user_id if isinstance(user_id, UUID) else UUID(user_id))

        # 生成OSS路径
        file_ext = os.path.splitext(file.filename)[1]
        object_key = oss_client.generate_object_key(
            user_id, "voices", file_ext
        )

        # 上传到OSS
        file_url = await oss_client.upload_file(
            file_data=contents,
            key=object_key,
            content_type=file.content_type
        )

        # 创建资产记录
        asset = Asset(
            user_id=user_id,
            type=AssetType.VOICE,
            title=title,
            source="upload",
            status="ready",
            is_system=False,
            file_url=file_url,
            file_size_bytes=len(contents),
            file_mime_type=file.content_type,
            meta_data={
                "original_filename": file.filename,
                "gender": gender,
                "tags": tags or []
            }
        )
        self.db.add(asset)
        self.db.flush()

        # 添加标签
        if tags:
            for tag in tags:
                asset_tag = AssetTag(asset_id=asset.id, tag=tag)
                self.db.add(asset_tag)

        self.db.commit()
        self.db.refresh(asset)

        return self._serialize_asset(asset)

    async def create_script(
        self,
        user_id: str,
        title: str,
        content: str,
        tags: Optional[List[str]] = None
    ) -> Dict:
        """
        创建脚本资产

        Args:
            user_id: 用户ID
            title: 脚本标题
            content: 脚本内容
            tags: 标签列表

        Returns:
            创建的资产信息
        """
        word_count = len(content)
        estimated_seconds = max(5, word_count // 7)  # 假设每秒7个字

        asset = Asset(
            user_id=user_id,
            type=AssetType.SCRIPT,
            title=title,
            content=content,
            source="upload",
            status="ready",
            is_system=False,
            meta_data={
                "word_count": word_count,
                "estimated_seconds": estimated_seconds,
                "tags": tags or []
            }
        )
        self.db.add(asset)
        self.db.flush()

        # 添加标签
        if tags:
            for tag in tags:
                asset_tag = AssetTag(asset_id=asset.id, tag=tag)
                self.db.add(asset_tag)

        self.db.commit()
        self.db.refresh(asset)

        return self._serialize_asset(asset)

    async def update_asset(
        self,
        asset_id: str,
        user_id: str,
        data: Dict
    ) -> Dict:
        """
        更新资产信息

        Args:
            asset_id: 资产ID
            user_id: 用户ID
            data: 更新数据

        Returns:
            更新后的资产信息

        Raises:
            ValueError: 资产不存在或无权修改
        """
        asset = self.db.query(Asset).filter(Asset.id == asset_id).first()

        if not asset:
            raise ValueError("资产不存在")

        if asset.user_id != user_id:
            raise ValueError("只能修改自己的资产")

        if "title" in data:
            asset.title = data["title"]
        if "description" in data:
            asset.description = data["description"]
        if "metadata" in data:
            asset.meta_data.update(data["metadata"])

        self.db.commit()
        self.db.refresh(asset)

        return self._serialize_asset(asset)

    async def delete_asset(self, asset_id: str, user_id: str):
        """
        删除资产

        Args:
            asset_id: 资产ID
            user_id: 用户ID

        Raises:
            ValueError: 资产不存在或无权删除
        """
        asset = self.db.query(Asset).filter(Asset.id == asset_id).first()

        if not asset:
            raise ValueError("资产不存在")

        if asset.user_id != user_id:
            raise ValueError("只能删除自己的资产")

        if asset.is_system:
            raise ValueError("不能删除系统资产")

        if asset.use_count > 0:
            raise ValueError("资产已被使用，无法删除")

        self.db.delete(asset)
        self.db.commit()

    async def _validate_image_file(self, file: UploadFile):
        """验证图片文件"""
        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in allowed_extensions:
            raise ValueError(f"不支持的图片格式: {file_ext}")

        MAX_SIZE = 20 * 1024 * 1024  # 20MB
        contents = await file.read()

        if len(contents) > MAX_SIZE:
            raise ValueError("文件大小超过20MB限制")

        await file.seek(0)

    async def _validate_audio_file(self, file: UploadFile):
        """验证音频文件"""
        allowed_extensions = {".mp3", ".wav", ".m4a"}
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in allowed_extensions:
            raise ValueError(f"不支持的音频格式: {file_ext}")

        MAX_SIZE = 20 * 1024 * 1024  # 20MB
        contents = await file.read()

        if len(contents) > MAX_SIZE:
            raise ValueError("文件大小超过20MB限制")

        await file.seek(0)

    def _serialize_asset(self, asset: Asset) -> Dict:
        """序列化资产对象"""
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
            "tags": [tag.tag for tag in asset.tags] if asset.tags else []
        }
