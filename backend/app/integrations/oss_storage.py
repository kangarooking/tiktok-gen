"""
阿里云OSS存储集成
"""
import oss2
import uuid
from typing import Optional, Dict, Tuple
from app.config import settings
from app.integrations.base import CloudStorageClientBase


# Legacy alias for backward compatibility
OSSStorageClient = "OSSClient"


class OSSClient(CloudStorageClientBase):
    """阿里云OSS存储客户端"""

    @classmethod
    def get_provider_name(cls) -> str:
        return "aliyun_oss"

    @classmethod
    def get_category(cls) -> str:
        return "cloud_storage"

    @classmethod
    def get_required_fields(cls) -> list:
        return ["access_key_id", "access_key_secret", "bucket_name", "endpoint", "public_base_url"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        # Use config values or fall back to settings
        access_key_id = self.get_config_value("access_key_id") or settings.OSS_ACCESS_KEY_ID
        access_key_secret = self.get_config_value("access_key_secret") or settings.OSS_ACCESS_KEY_SECRET
        endpoint = self.get_config_value("endpoint") or settings.OSS_ENDPOINT
        bucket_name = self.get_config_value("bucket_name") or settings.OSS_BUCKET_NAME
        self.public_base_url = self.get_config_value("public_base_url") or settings.OSS_PUBLIC_BASE_URL

        self.auth = oss2.Auth(access_key_id, access_key_secret)

        # 创建 oss2 Session 并禁用代理
        session = oss2.Session()
        # 禁用所有代理设置
        session.proxies = {}

        self.bucket = oss2.Bucket(
            self.auth,
            endpoint,
            bucket_name,
            session=session
        )

    async def validate_config(self) -> Tuple[bool, Optional[str]]:
        """Validate the configuration"""
        is_valid, error = self.validate_required_fields()
        if not is_valid:
            return is_valid, error

        try:
            # Try to list objects (limited) to verify credentials
            self.bucket.list_objects(max_keys=1)
            return True, None
        except Exception as e:
            return False, f"OSS credentials invalid: {str(e)}"

    async def upload_file(
        self,
        file_data: bytes,
        key: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload a file to cloud storage

        Args:
            file_data: File content as bytes
            key: Storage key/path
            content_type: MIME type

        Returns:
            Public URL of the uploaded file
        """
        return await self.upload_file_async(key, file_data, content_type)

    async def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600
    ) -> str:
        """
        Get a presigned URL for a file

        Args:
            key: Storage key/path
            expires_in: URL expiration time in seconds

        Returns:
            Presigned URL
        """
        return self.generate_presigned_url(key, expires_in)

    async def upload_file_async(
        self,
        object_key: str,
        file_data: bytes,
        content_type: Optional[str] = None
    ) -> str:
        """
        上传文件到OSS

        Args:
            object_key: 对象键（文件路径）
            file_data: 文件数据
            content_type: Content-Type

        Returns:
            公网URL

        Raises:
            Exception: 上传失败
        """
        # 设置headers
        headers = {}
        if content_type:
            headers['Content-Type'] = content_type

        # 上传
        result = self.bucket.put_object(
            object_key,
            file_data,
            headers=headers
        )

        if result.status != 200:
            raise Exception(f"OSS上传失败: {result}")

        # 返回公网URL
        return f"{self.public_base_url}/{object_key}"

    def generate_presigned_url(
        self,
        object_key: str,
        expires: int = 3600
    ) -> str:
        """
        生成预签名上传URL

        Args:
            object_key: 对象键
            expires: 过期时间（秒）

        Returns:
            预签名URL
        """
        url = self.bucket.sign_url('PUT', object_key, expires)
        return url

    def delete_file(self, object_key: str) -> bool:
        """
        删除文件

        Args:
            object_key: 对象键

        Returns:
            是否成功
        """
        try:
            self.bucket.delete_object(object_key)
            return True
        except Exception as e:
            self.logger.error(f"OSS删除失败: {e}")
            return False

    def generate_object_key(
        self,
        user_id: str,
        category: str,
        file_type: str,
        original_filename: Optional[str] = None
    ) -> str:
        """
        生成对象键

        Args:
            user_id: 用户ID
            category: 分类 (avatars, voices, scripts, videos, etc.)
            file_type: 文件扩展名
            original_filename: 原始文件名（可选）

        Returns:
            对象键
        """
        # 格式: users/{user_id}/{category}/{uuid}{ext}
        ext = file_type if file_type.startswith(".") else f".{file_type}"
        unique_id = str(uuid.uuid4())
        return f"users/{user_id}/{category}/{unique_id}{ext}"


# Backward compatibility alias
OSSStorageClient = OSSClient
