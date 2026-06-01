"""
Agnes Video V2.0 integration.
"""
import asyncio
from typing import Any, Dict, Optional, Tuple

import httpx

from app.integrations.base import DigitalHumanClientBase
from app.integrations.client_factory import register_client


@register_client
class AgnesVideoClient(DigitalHumanClientBase):
    """Agnes async video generation client."""

    @classmethod
    def get_provider_name(cls) -> str:
        return "agnes_video"

    @classmethod
    def get_category(cls) -> str:
        return "digital_human"

    @classmethod
    def requires_tts_audio(cls) -> bool:
        return False

    @classmethod
    def supports_storyboard_images(cls) -> bool:
        return True

    @classmethod
    def supports_audio_sync_prompt(cls) -> bool:
        return True

    @classmethod
    def get_required_fields(cls) -> list:
        return ["api_key", "base_url", "model"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = self.get_config_value("api_key")
        self.base_url = self.get_config_value("base_url", "https://apihub.agnes-ai.com/v1").rstrip("/")
        self.model = self.get_config_value("model", "agnes-video-v2.0")
        self.width = int(self.get_config_value("width", 1152))
        self.height = int(self.get_config_value("height", 768))
        self.num_frames = int(self.get_config_value("num_frames", 193))
        self.frame_rate = int(self.get_config_value("frame_rate", 24))
        self.steps = self.get_config_value("steps")
        self.negative_prompt = self.get_config_value("negative_prompt")
        self.poll_interval = int(self.get_config_value("poll_interval", 5))
        self.timeout = int(self.get_config_value("timeout", 1800))

    async def validate_config(self) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required_fields()
        if not is_valid:
            return is_valid, error
        if self.num_frames > 441 or (self.num_frames - 1) % 8 != 0:
            return False, "num_frames must be <= 441 and satisfy 8n + 1"
        if self.frame_rate < 1 or self.frame_rate > 60:
            return False, "frame_rate must be between 1 and 60"
        return True, None

    async def create_video_task(
        self,
        audio_url: Optional[str] = None,
        image_url: Optional[str] = None,
        prompt: str = "",
        resolution: Optional[str] = None,
        seed: int = -1,
        **kwargs
    ) -> str:
        if not prompt:
            raise ValueError("Agnes Video prompt is required")

        storyboard_urls = kwargs.get("storyboard_image_urls") or []
        storyboard_mode = kwargs.get("storyboard_mode") or "none"

        payload: Dict[str, Any] = {
            "model": kwargs.get("model") or self.model,
            "prompt": prompt,
            "height": int(kwargs.get("height") or self.height),
            "width": int(kwargs.get("width") or self.width),
            "num_frames": int(kwargs.get("num_frames") or self.num_frames),
            "frame_rate": int(kwargs.get("frame_rate") or self.frame_rate),
        }
        if seed is not None and int(seed) >= 0:
            payload["seed"] = int(seed)
        if kwargs.get("steps") or self.steps:
            payload["steps"] = int(kwargs.get("steps") or self.steps)
        if kwargs.get("negative_prompt") or self.negative_prompt:
            payload["negative_prompt"] = kwargs.get("negative_prompt") or self.negative_prompt

        images = [url for url in storyboard_urls if url]
        if not images and image_url:
            images = [image_url]

        if len(images) == 1:
            payload["image"] = images[0]
        elif len(images) > 1:
            payload["extra_body"] = {"image": images}
            if storyboard_mode == "keyframes":
                payload["extra_body"]["mode"] = "keyframes"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.base_url}/videos", json=payload, headers=headers)
            if response.status_code >= 400:
                raise Exception(f"Agnes Video create task failed: {response.status_code} - {response.text}")
            data = response.json()

        task_id = data.get("id")
        if not task_id and isinstance(data.get("data"), dict):
            task_id = data["data"].get("id")
        if not task_id:
            raise Exception(f"Agnes Video create task returned no id: {data}")
        return str(task_id)

    async def get_task_result(self, task_id: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(f"{self.base_url}/videos/{task_id}", headers=headers)
            if response.status_code >= 400:
                raise Exception(f"Agnes Video query task failed: {response.status_code} - {response.text}")
            data = response.json()

        source = data.get("data") if isinstance(data.get("data"), dict) else data
        status = str(source.get("status", "")).lower()
        error = source.get("error") or source.get("message")
        if error and status not in {"completed", "succeeded", "success", "done"}:
            status = "failed"
        return {
            "status": status,
            "progress": source.get("progress"),
            "video_url": self._extract_video_url(source),
            "error": error,
            "raw": data,
        }

    @staticmethod
    def _extract_video_url(source: Dict[str, Any]) -> Optional[str]:
        for key in ("video_url", "url", "output_url", "remixed_from_video_id"):
            if isinstance(source.get(key), str):
                return source[key]

        output = source.get("output") or source.get("outputs")
        if isinstance(output, str):
            return output
        if isinstance(output, list):
            for item in output:
                if isinstance(item, str):
                    return item
                if isinstance(item, dict):
                    for key in ("video_url", "url", "output_url", "remixed_from_video_id"):
                        if isinstance(item.get(key), str):
                            return item[key]

        for key in ("video", "result", "content"):
            value = source.get(key)
            if isinstance(value, dict):
                nested = AgnesVideoClient._extract_video_url(value)
                if nested:
                    return nested
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        nested = AgnesVideoClient._extract_video_url(item)
                        if nested:
                            return nested
        return None

    async def wait_for_completion(self, task_id: str, max_wait_seconds: int = 600) -> str:
        waited = 0
        interval = max(1, self.poll_interval)
        limit = min(max_wait_seconds or self.timeout, self.timeout)

        while waited < limit:
            result = await self.get_task_result(task_id)
            status = result["status"]
            if status in {"completed", "succeeded", "success", "done"}:
                if result.get("video_url"):
                    return result["video_url"]
                raise Exception(f"Agnes Video task completed but no video URL: {result.get('raw')}")
            if status in {"failed", "error", "cancelled", "canceled"}:
                raise Exception(result.get("error") or f"Agnes Video task failed: {result.get('raw')}")
            await asyncio.sleep(interval)
            waited += interval

        raise TimeoutError(f"Agnes Video task timeout after {limit}s: {task_id}")

    async def generate_video(self, avatar_image_url: str, audio_url: str, **kwargs) -> str:
        task_id = await self.create_video_task(
            audio_url=audio_url,
            image_url=avatar_image_url,
            prompt=kwargs.get("prompt", ""),
            seed=kwargs.get("seed", -1),
            **kwargs,
        )
        return await self.wait_for_completion(task_id, kwargs.get("max_wait_seconds", self.timeout))
