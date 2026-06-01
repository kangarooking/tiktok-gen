"""
Agnes Image 2.1 Flash integration.
"""
import base64
from typing import Any, Dict, Optional, Tuple

import httpx

from app.integrations.base import AIImageClientBase
from app.integrations.client_factory import register_client


@register_client
class AgnesImageClient(AIImageClientBase):
    """Agnes image generation and image-to-image client."""

    @classmethod
    def get_provider_name(cls) -> str:
        return "agnes_image"

    @classmethod
    def get_category(cls) -> str:
        return "ai_image"

    @classmethod
    def get_required_fields(cls) -> list:
        return ["api_key", "base_url", "model"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = self.get_config_value("api_key")
        self.base_url = self.get_config_value("base_url", "https://apihub.agnes-ai.com/v1").rstrip("/")
        self.model = self.get_config_value("model", "agnes-image-2.1-flash")
        self.default_size = self.get_config_value("size", "1024x768")
        self.timeout = int(self.get_config_value("timeout", 180))

    async def validate_config(self) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required_fields()
        if not is_valid:
            return is_valid, error
        return True, None

    async def generate_image(self, prompt: str, **kwargs) -> str:
        result = await self.generate_image_with_metadata(prompt, **kwargs)
        return result["image_url"]

    async def generate_image_with_metadata(
        self,
        prompt: str,
        reference_images: Optional[list[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": kwargs.get("model") or self.model,
            "prompt": prompt,
            "size": kwargs.get("size") or self.default_size,
        }

        image_urls = kwargs.get("image_urls") or reference_images or []
        if image_urls:
            payload["extra_body"] = {
                "image": [self._normalize_image(value) for value in image_urls],
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/images/generations",
                json=payload,
                headers=headers,
            )
            if response.status_code >= 400:
                raise Exception(f"Agnes Image API error: {response.status_code} - {response.text}")
            data = response.json()

        image_url = self._extract_image_url(data)
        if not image_url:
            raise Exception(f"Agnes Image returned no image URL: {data}")

        return {
            "image_url": image_url,
            "provider": self.get_provider_name(),
            "model": payload["model"],
            "size": payload["size"],
            "raw": data,
        }

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
    def _extract_image_url(data: Dict[str, Any]) -> Optional[str]:
        if isinstance(data.get("url"), str):
            return data["url"]
        for key in ("image_url", "output_url"):
            if isinstance(data.get(key), str):
                return data[key]
        items = data.get("data")
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                if isinstance(item.get("url"), str):
                    return item["url"]
                if isinstance(item.get("image_url"), str):
                    return item["image_url"]
        images = data.get("images")
        if isinstance(images, list) and images:
            first = images[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict) and isinstance(first.get("url"), str):
                return first["url"]
        return None

    async def generate_avatar_image(
        self,
        description: str,
        style: str = None,
        gender: str = None,
        age_range: str = None,
        reference_images: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        prompt = _build_asset_image_prompt(description, style, gender, age_range, bool(reference_images))
        return await self.generate_image_with_metadata(prompt, reference_images=reference_images)


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

    reference_line = "请参考上传的图片，但以用户提示词为主。" if has_reference_images else "只生成用户提示词中明确要求的主体。"
    constraint_text = "\n".join(constraints)
    if constraint_text:
        constraint_text = f"\n补充约束：\n{constraint_text}"

    return f"""请根据用户提示词生成一张图片。
{reference_line}
{constraint_text}

用户提示词：
{description}

要求：
- 严格遵循用户提示词，不要添加未被要求的主体或角色。
- 如果用户要求文字，请按用户原文绘制；否则不要添加无关文字、水印或 UI。
- 保持画面清晰、构图完整、主体明确。"""
