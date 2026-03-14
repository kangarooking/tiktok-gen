"""
Custom Digital Human 服务集成

支持自定义数字人视频生成 API
"""
import httpx
import asyncio
from typing import Optional, Dict, Tuple
from app.integrations.base import DigitalHumanClientBase
from app.integrations.client_factory import register_client


@register_client
class CustomDigitalHumanClient(DigitalHumanClientBase):
    """Custom Digital Human API 客户端"""

    @classmethod
    def get_provider_name(cls) -> str:
        return "custom"

    @classmethod
    def get_category(cls) -> str:
        return "digital_human"

    @classmethod
    def get_required_fields(cls) -> list:
        return ["base_url"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = self.get_config_value("api_key")
        self.base_url = self.get_config_value("base_url", "").rstrip("/")
        self.model = self.get_config_value("model")
        self.timeout = self.get_config_value("timeout") or 300

    async def validate_config(self) -> Tuple[bool, Optional[str]]:
        """Validate the configuration"""
        is_valid, error = self.validate_required_fields()
        if not is_valid:
            return is_valid, error
        if not self.base_url:
            return False, "base_url is required"
        return True, None

    async def create_video_task(
        self,
        audio_url: str,
        image_url: Optional[str] = None,
        prompt: str = "",
        resolution: str = "480p",
        seed: int = -1,
        **kwargs
    ) -> str:
        """
        Create a video generation task

        Args:
            audio_url: URL of the audio file
            image_url: URL of the avatar image
            prompt: Performance prompt
            resolution: Video resolution
            seed: Random seed

        Returns:
            Task ID
        """
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "audio_url": audio_url,
            "image_url": image_url,
            "prompt": prompt,
            "resolution": resolution,
            "seed": seed if seed > 0 else None
        }
        if self.model:
            payload["model"] = self.model

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/video/create",
                json=payload,
                headers=headers
            )

            if response.status_code != 200:
                raise Exception(f"Digital Human API error: {response.status_code} - {response.text}")

            data = response.json()

            # Try different response formats
            if "task_id" in data:
                return data["task_id"]
            elif "id" in data:
                return data["id"]
            elif "data" in data and isinstance(data["data"], dict):
                return data["data"].get("task_id") or data["data"].get("id")
            else:
                raise Exception(f"Unexpected response format: {data}")

    async def get_task_status(self, task_id: str) -> Dict:
        """
        Get task status

        Args:
            task_id: Task ID

        Returns:
            Status dict with 'status' and optionally 'video_url'
        """
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/video/status/{task_id}",
                headers=headers
            )

            if response.status_code != 200:
                raise Exception(f"Status API error: {response.status_code} - {response.text}")

            data = response.json()

            # Normalize response format
            if "data" in data and isinstance(data["data"], dict):
                return {
                    "status": data["data"].get("status", "unknown"),
                    "video_url": data["data"].get("video_url") or data["data"].get("url"),
                    "progress": data["data"].get("progress", 0)
                }
            else:
                return {
                    "status": data.get("status", "unknown"),
                    "video_url": data.get("video_url") or data.get("url"),
                    "progress": data.get("progress", 0)
                }

    async def wait_for_completion(
        self,
        task_id: str,
        max_wait_seconds: int = 600,
        poll_interval: int = 5
    ) -> str:
        """
        Wait for video generation to complete

        Args:
            task_id: Task ID
            max_wait_seconds: Maximum wait time
            poll_interval: Polling interval in seconds

        Returns:
            Video URL

        Raises:
            Exception: If generation fails or times out
        """
        waited = 0
        while waited < max_wait_seconds:
            status = await self.get_task_status(task_id)

            if status["status"] in ["completed", "complete", "success", "done"]:
                if status.get("video_url"):
                    return status["video_url"]
                else:
                    raise Exception("Task completed but no video URL returned")

            elif status["status"] in ["failed", "error", "cancelled"]:
                raise Exception(f"Video generation failed: {status}")

            await asyncio.sleep(poll_interval)
            waited += poll_interval

        raise Exception(f"Video generation timed out after {max_wait_seconds} seconds")

    async def generate_video(
        self,
        avatar_image_url: str,
        audio_url: str,
        **kwargs
    ) -> str:
        """Compatibility method required by DigitalHumanClientBase."""
        task_id = await self.create_video_task(
            audio_url=audio_url,
            image_url=avatar_image_url,
            prompt=kwargs.get("prompt", ""),
            resolution=kwargs.get("resolution", "480p"),
            seed=kwargs.get("seed", -1),
            **kwargs,
        )
        return await self.wait_for_completion(task_id)
