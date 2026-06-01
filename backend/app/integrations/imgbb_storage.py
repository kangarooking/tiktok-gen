"""
ImgBB image hosting integration.
"""
import base64
import os
from pathlib import PurePosixPath
from typing import Dict, Optional, Tuple

import httpx

from app.config import settings
from app.integrations.base import CloudStorageClientBase
from app.integrations.client_factory import register_client


@register_client
class ImgBBClient(CloudStorageClientBase):
    """ImgBB-backed image storage client."""

    @classmethod
    def get_provider_name(cls) -> str:
        return "imgbb"

    @classmethod
    def get_category(cls) -> str:
        return "cloud_storage"

    @classmethod
    def get_required_fields(cls) -> list:
        return ["api_key", "base_url"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = (
            self.get_config_value("api_key")
            or os.environ.get("IMGBB_API_KEY")
            or settings.IMGBB_API_KEY
        )
        self.base_url = (
            self.get_config_value("base_url")
            or settings.IMGBB_BASE_URL
            or "https://api.imgbb.com/1/upload"
        ).rstrip("/")
        self.expiration = int(self.get_config_value("expiration", settings.IMGBB_EXPIRATION or 0) or 0)
        self.timeout = int(self.get_config_value("timeout", 60) or 60)

    async def validate_config(self) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required_fields()
        if not is_valid:
            return is_valid, error
        return True, None

    async def upload_file(
        self,
        file_data: bytes,
        key: str,
        content_type: Optional[str] = None
    ) -> str:
        if not file_data:
            raise ValueError("ImgBB upload requires non-empty file data")

        image_base64 = base64.b64encode(file_data).decode("utf-8")
        name = self._name_from_key(key)
        payload = {
            "key": self.api_key,
            "image": image_base64,
            "name": name,
        }
        if self.expiration > 0:
            payload["expiration"] = str(self.expiration)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.base_url, data=payload)
            if response.status_code >= 400:
                raise Exception(f"ImgBB upload failed: {response.status_code} - {response.text}")
            data = response.json()

        if not data.get("success"):
            error = data.get("error", {}).get("message") or data
            raise Exception(f"ImgBB upload failed: {error}")

        image = data.get("data") or {}
        url = image.get("url") or image.get("display_url")
        if not url:
            raise Exception(f"ImgBB upload returned no URL: {data}")
        return str(url)

    async def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600
    ) -> str:
        raise NotImplementedError("ImgBB does not support presigned upload URLs")

    def generate_object_key(
        self,
        user_id: str,
        category: str,
        file_type: str,
        original_filename: Optional[str] = None
    ) -> str:
        ext = file_type if file_type.startswith(".") else f".{file_type}"
        if original_filename:
            name = PurePosixPath(original_filename).stem
        else:
            import uuid
            name = str(uuid.uuid4())
        return f"users/{user_id}/{category}/{name}{ext}"

    @staticmethod
    def _name_from_key(key: str) -> str:
        name = PurePosixPath(key or "image").stem
        return name[:100] or "image"
