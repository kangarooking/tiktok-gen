"""
APIMart GPT-Image-2 integration.
"""
import base64
import os
from typing import Any, Dict, Optional, Tuple

import httpx

from app.integrations.base import AIImageClientBase
from app.integrations.client_factory import register_client


RUNNING_STATES = {"submitted", "pending", "processing", "in_progress"}
DONE_STATES = {"completed"}
FAILED_STATES = {"failed", "cancelled", "canceled"}


@register_client
class APIMartGPTImage2Client(AIImageClientBase):
    """APIMart hosted GPT-Image-2 task API client."""

    @classmethod
    def get_provider_name(cls) -> str:
        return "apimart_gpt_image2"

    @classmethod
    def get_category(cls) -> str:
        return "ai_image"

    @classmethod
    def get_required_fields(cls) -> list:
        return ["api_key", "base_url", "model"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = (
            self.get_config_value("api_key")
            or os.environ.get("APIMART_API_KEY")
            or os.environ.get("APIMART_TOKEN")
        )
        self.base_url = self.get_config_value("base_url", "https://api.apimart.ai").rstrip("/")
        self.model = self.get_config_value("model", "gpt-image-2")
        self.size = self.get_config_value("size", "9:16")
        self.resolution = self.get_config_value("resolution", "1k")
        self.official_fallback = self._to_bool(self.get_config_value("official_fallback"), False)
        self.language = self.get_config_value("language", "en")
        self.poll_interval = int(self.get_config_value("poll_interval", 5))
        self.timeout = int(self.get_config_value("timeout", 300))

    async def validate_config(self) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required_fields()
        if not is_valid:
            return is_valid, error
        return True, None

    async def generate_image(self, prompt: str, **kwargs) -> str:
        result = await self.generate_image_with_metadata(prompt, **kwargs)
        return result["image_url"]

    async def generate_avatar_image(
        self,
        description: str,
        style: str = None,
        gender: str = None,
        age_range: str = None,
        reference_images: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        prompt = self._build_asset_image_prompt(description, style, gender, age_range, bool(reference_images))
        return await self.generate_image_with_metadata(prompt, reference_images=reference_images)

    async def generate_image_with_metadata(
        self,
        prompt: str,
        reference_images: Optional[list[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        payload = {
            "model": kwargs.get("model") or self.model,
            "prompt": prompt,
            "n": int(kwargs.get("n") or 1),
            "size": kwargs.get("size") or self.size,
            "resolution": kwargs.get("resolution") or self.resolution,
        }
        image_urls = kwargs.get("image_urls") or reference_images or []
        if image_urls:
            payload["image_urls"] = [self._normalize_image(value) for value in image_urls]
        if self._to_bool(kwargs.get("official_fallback"), self.official_fallback):
            payload["official_fallback"] = True

        submit_response = await self._request_json("POST", "/v1/images/generations", payload)
        task_id = self._extract_task_id(submit_response)
        task_response = await self._poll_task(task_id)
        image_urls = self._extract_image_urls(task_response)
        if not image_urls:
            raise Exception(f"APIMart GPT-Image-2 returned no image URL: {task_response}")

        return {
            "image_url": image_urls[0],
            "provider": self.get_provider_name(),
            "model": payload["model"],
            "size": payload["size"],
            "resolution": payload["resolution"],
            "task_id": task_id,
            "raw": task_response,
        }

    async def _request_json(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if payload is not None:
            headers["Content-Type"] = "application/json"

        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                json=payload,
                headers=headers,
            )
            if response.status_code >= 400:
                raise Exception(f"APIMart API error: {response.status_code} - {response.text}")
            data = response.json()

        if data.get("error"):
            raise Exception(f"APIMart API error: {data['error']}")
        return data

    async def _poll_task(self, task_id: str) -> Dict[str, Any]:
        waited = 0
        while waited < self.timeout:
            response = await self._request_json("GET", f"/v1/tasks/{task_id}?language={self.language}")
            data = response.get("data") or {}
            status = str(data.get("status", "")).lower()
            if status in DONE_STATES:
                return response
            if status in FAILED_STATES:
                raise Exception(f"APIMart task {task_id} failed: {data.get('error') or data}")
            if status and status not in RUNNING_STATES:
                self.logger.warning(f"Unknown APIMart task status: {status}")

            import asyncio
            await asyncio.sleep(self.poll_interval)
            waited += self.poll_interval

        raise TimeoutError(f"APIMart task timeout after {self.timeout}s: {task_id}")

    @staticmethod
    def _extract_task_id(response: Dict[str, Any]) -> str:
        data = response.get("data")
        if isinstance(data, list) and data and isinstance(data[0], dict) and data[0].get("task_id"):
            return str(data[0]["task_id"])
        raise Exception(f"Could not find APIMart task_id in response: {response}")

    @staticmethod
    def _extract_image_urls(task_response: Dict[str, Any]) -> list[str]:
        data = task_response.get("data", {})
        result = data.get("result", {}) if isinstance(data, dict) else {}
        images = result.get("images", []) if isinstance(result, dict) else []
        urls: list[str] = []
        for image in images:
            if not isinstance(image, dict):
                continue
            value = image.get("url", [])
            if isinstance(value, str):
                urls.append(value)
            elif isinstance(value, list):
                urls.extend(str(url) for url in value if url)
        return urls

    @staticmethod
    def _normalize_image(value: str) -> str:
        if value.startswith(("http://", "https://", "data:image/")):
            return value
        try:
            base64.b64decode(value, validate=True)
            return f"data:image/jpeg;base64,{value}"
        except Exception:
            return value

    @staticmethod
    def _to_bool(value: Any, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

    @staticmethod
    def _build_asset_image_prompt(
        description: str,
        style: Optional[str] = None,
        gender: Optional[str] = None,
        age_range: Optional[str] = None,
        has_reference_images: bool = False,
    ) -> str:
        constraints = []
        if style:
            constraints.append(f"- 风格：{style}")
        if gender:
            constraints.append(f"- 性别：{gender}")
        if age_range:
            constraints.append(f"- 年龄：{age_range}")
        constraint_text = "\n".join(constraints)
        if constraint_text:
            constraint_text = f"\n补充约束：\n{constraint_text}"
        reference_line = "请参考上传的图片，但以用户提示词为主。" if has_reference_images else "只生成用户提示词中明确要求的主体。"
        return f"""请根据用户提示词生成一张图片。
{reference_line}
{constraint_text}

用户提示词：
{description}

要求：
- 严格遵循用户提示词，不要添加未被要求的主体或角色。
- 如果用户要求文字，请按用户原文绘制；否则不要添加无关文字、水印或 UI。
- 保持画面清晰、构图完整、主体明确。"""
