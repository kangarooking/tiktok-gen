"""
VolcEngine Ark Seedance integration.
"""
import asyncio
from typing import Dict, Optional, Tuple, Any

import httpx

from app.config import settings
from app.integrations.base import DigitalHumanClientBase
from app.integrations.client_factory import register_client


@register_client
class ArkSeedanceClient(DigitalHumanClientBase):
    """VolcEngine Ark Seedance video generation client."""

    @classmethod
    def get_provider_name(cls) -> str:
        return "ark_seedance"

    @classmethod
    def get_category(cls) -> str:
        return "digital_human"

    @classmethod
    def get_required_fields(cls) -> list:
        return ["api_key", "base_url", "model"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = self.get_config_value("api_key") or settings.ARK_API_KEY
        self.base_url = (self.get_config_value("base_url") or settings.ARK_BASE_URL).rstrip("/")
        self.model = self.get_config_value("model") or settings.ARK_SEEDANCE_MODEL
        self.timeout = int(self.get_config_value("timeout") or settings.ARK_TIMEOUT)
        self.poll_interval = int(self.get_config_value("poll_interval") or settings.ARK_POLL_INTERVAL_SECONDS)
        self.default_duration = int(self.get_config_value("duration") or settings.ARK_SEEDANCE_DURATION)
        self.default_resolution = str(self.get_config_value("resolution") or settings.ARK_SEEDANCE_RESOLUTION)
        self.default_aspect_ratio = str(self.get_config_value("aspect_ratio") or settings.ARK_SEEDANCE_ASPECT_RATIO)
        self.default_watermark = self._to_bool(self.get_config_value("watermark"), settings.ARK_SEEDANCE_WATERMARK)
        self.default_camera_fixed = self._to_bool(self.get_config_value("camera_fixed"), settings.ARK_SEEDANCE_CAMERA_FIXED)
        self.default_extra_flags = str(self.get_config_value("extra_flags") or settings.ARK_SEEDANCE_EXTRA_FLAGS).strip()

    async def validate_config(self) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required_fields()
        if not is_valid:
            return is_valid, error
        return True, None

    @staticmethod
    def _to_bool(value: Any, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        s = str(value).strip().lower()
        if s in {"1", "true", "yes", "y", "on"}:
            return True
        if s in {"0", "false", "no", "n", "off"}:
            return False
        return default

    def _append_prompt_flags(self, prompt: str, **kwargs) -> str:
        duration = kwargs.get("duration", self.default_duration)
        resolution = kwargs.get("resolution", self.default_resolution)
        aspect_ratio = kwargs.get("aspect_ratio", self.default_aspect_ratio)
        camera_fixed = self._to_bool(kwargs.get("camera_fixed"), self.default_camera_fixed)
        watermark = self._to_bool(kwargs.get("watermark"), self.default_watermark)
        extra_flags = str(kwargs.get("extra_flags") or self.default_extra_flags or "").strip()

        final_prompt = (prompt or "").strip()
        lower_prompt = final_prompt.lower()

        def maybe_add(flag: str, value: Any):
            nonlocal final_prompt, lower_prompt
            if f"--{flag}" in lower_prompt:
                return
            final_prompt = f"{final_prompt} --{flag} {value}".strip()
            lower_prompt = final_prompt.lower()

        if duration:
            maybe_add("duration", int(duration))
        if resolution:
            maybe_add("resolution", resolution)
        if aspect_ratio:
            maybe_add("aspectratio", aspect_ratio)
        maybe_add("camerafixed", str(camera_fixed).lower())
        maybe_add("watermark", str(watermark).lower())

        if extra_flags:
            final_prompt = f"{final_prompt} {extra_flags}".strip()

        return final_prompt

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
        Create Ark Seedance video generation task.

        Notes:
        - audio_url is ignored for Seedance flow.
        - prompt should already contain merged "video prompt + script speech content".
        """
        if not prompt:
            raise ValueError("Seedance prompt is required")

        prompt = self._append_prompt_flags(
            prompt,
            duration=kwargs.get("duration"),
            resolution=kwargs.get("resolution"),
            aspect_ratio=kwargs.get("aspect_ratio"),
            camera_fixed=kwargs.get("camera_fixed"),
            watermark=kwargs.get("watermark"),
            extra_flags=kwargs.get("extra_flags"),
        )

        content = [{"type": "text", "text": prompt}]
        if image_url:
            content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })

        payload = {
            "model": self.model,
            "content": content,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/contents/generations/tasks",
                json=payload,
                headers=headers,
            )
            if response.status_code >= 400:
                raise Exception(f"Ark Seedance create task failed: {response.status_code} - {response.text}")

            result = response.json()

        task_id = result.get("id")
        if not task_id and isinstance(result.get("data"), dict):
            task_id = result["data"].get("id")
        if not task_id:
            raise Exception(f"Ark Seedance create task returned no id: {result}")
        return str(task_id)

    @staticmethod
    def _extract_video_url(result: Dict[str, Any]) -> Optional[str]:
        if result.get("video_url"):
            return result.get("video_url")
        if isinstance(result.get("data"), dict) and result["data"].get("video_url"):
            return result["data"]["video_url"]
        content = result.get("content")
        if isinstance(content, dict):
            if content.get("video_url"):
                return content.get("video_url")
            if isinstance(content.get("video"), dict) and content["video"].get("url"):
                return content["video"]["url"]
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("video_url"):
                    return item.get("video_url")
                if isinstance(item.get("video"), dict) and item["video"].get("url"):
                    return item["video"]["url"]
        return None

    async def get_task_result(self, task_id: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                f"{self.base_url}/contents/generations/tasks/{task_id}",
                headers=headers,
            )
            if response.status_code >= 400:
                raise Exception(f"Ark Seedance query task failed: {response.status_code} - {response.text}")
            result = response.json()

        status = result.get("status")
        if not status and isinstance(result.get("data"), dict):
            status = result["data"].get("status")
        status = (status or "").lower()

        error_obj = result.get("error")
        error_message = None
        if isinstance(error_obj, dict):
            error_message = error_obj.get("message") or str(error_obj)
        elif error_obj:
            error_message = str(error_obj)

        return {
            "status": status,
            "video_url": self._extract_video_url(result),
            "error": error_message,
            "raw": result,
        }

    async def wait_for_completion(self, task_id: str, max_wait_seconds: int = 600) -> str:
        waited = 0
        interval = max(1, self.poll_interval)

        while waited < max_wait_seconds:
            result = await self.get_task_result(task_id)
            status = result["status"]

            if status in {"succeeded", "success", "completed", "done"}:
                if result.get("video_url"):
                    return result["video_url"]
                raise Exception(f"Ark Seedance task succeeded but no video url: {result.get('raw')}")

            if status in {"failed", "error", "cancelled", "canceled"}:
                raise Exception(result.get("error") or f"Ark Seedance task failed: {result.get('raw')}")

            await asyncio.sleep(interval)
            waited += interval

        raise TimeoutError(f"Ark Seedance task timeout after {max_wait_seconds}s: {task_id}")

    async def generate_video(
        self,
        avatar_image_url: str,
        audio_url: str,
        **kwargs
    ) -> str:
        task_id = await self.create_video_task(
            audio_url=audio_url,
            image_url=avatar_image_url,
            prompt=kwargs.get("prompt", ""),
            resolution=kwargs.get("resolution", "480p"),
            seed=kwargs.get("seed", -1),
            **kwargs,
        )
        return await self.wait_for_completion(task_id, max_wait_seconds=kwargs.get("max_wait_seconds", self.timeout))
