"""
Custom OpenAI-compatible 图片生成服务集成

支持任何兼容 OpenAI Chat Completions API 的图片生成服务
"""
import httpx
import re
from typing import Optional, Dict, Tuple
from app.integrations.base import AIImageClientBase
from app.integrations.client_factory import register_client


@register_client
class CustomOpenAIAIImageClient(AIImageClientBase):
    """Custom OpenAI-compatible API 客户端 for AI Image Generation"""

    @classmethod
    def get_provider_name(cls) -> str:
        return "custom_openai"

    @classmethod
    def get_category(cls) -> str:
        return "ai_image"

    @classmethod
    def get_required_fields(cls) -> list:
        return ["api_key", "base_url"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = self.get_config_value("api_key")
        self.base_url = self.get_config_value("base_url", "").rstrip("/")
        self.model = self.get_config_value("model") or "gpt-4-vision-preview"
        self.timeout = self.get_config_value("timeout") or 180  # AI图片生成需要较长超时时间

    async def validate_config(self) -> Tuple[bool, Optional[str]]:
        """Validate the configuration"""
        is_valid, error = self.validate_required_fields()
        if not is_valid:
            return is_valid, error

        if not self.base_url:
            return False, "base_url is required"

        return True, None

    async def generate_image(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """
        Generate an image from a prompt

        Args:
            prompt: Generation prompt

        Returns:
            URL of the generated image
        """
        reference_images = kwargs.get("reference_images")
        result = await self.generate_image_with_metadata(prompt, reference_images)
        return result["image_url"]

    async def generate_image_with_metadata(
        self,
        prompt: str,
        reference_images: Optional[list[str]] = None
    ) -> Dict:
        """
        生成图片

        Args:
            prompt: 图片生成提示词
            reference_images: 参考图片的 base64 编码列表（可选）

        Returns:
            包含图片URL的字典

        Raises:
            Exception: 生成失败
        """
        # 构建请求内容
        content_parts = [{"type": "text", "text": prompt}]

        # 如果有参考图片，添加到请求中（以图生图）
        if reference_images:
            for img_base64 in reference_images:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_base64}"
                    }
                })

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content_parts
                }
            ]
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )

            if response.status_code != 200:
                error_text = response.text
                raise Exception(f"API error: {response.status_code} - {error_text}")

            data = response.json()

            # 检查响应
            if "choices" not in data or len(data["choices"]) == 0:
                raise Exception("No image generated in response")

            # 从响应中提取图片URL
            # 返回格式: ![image](URL)
            content = data["choices"][0]["message"]["content"]
            image_url = self._extract_image_url(content)

            if not image_url:
                raise Exception("No image URL found in response")

            return {
                "image_url": image_url,
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                "total_tokens": data.get("usage", {}).get("total_tokens", 0)
            }

    def _extract_image_url(self, content: str) -> Optional[str]:
        """
        从 Markdown 内容中提取图片URL

        Args:
            content: Markdown格式的内容

        Returns:
            图片URL，如果未找到则返回None
        """
        # 匹配 ![image](URL) 格式
        pattern = r'!\[image\]\((https?://[^\)]+)\)'
        match = re.search(pattern, content)

        if match:
            return match.group(1)

        # 也尝试匹配 ![...](URL) 格式
        pattern2 = r'!\[.*?\]\((https?://[^\)]+)\)'
        match2 = re.search(pattern2, content)

        if match2:
            return match2.group(1)

        return None

    async def generate_avatar_image(
        self,
        description: str,
        style: str = None,
        gender: str = None,
        age_range: str = None,
        reference_images: Optional[list[str]] = None
    ) -> Dict:
        """
        生成头像图片

        Args:
            description: 头像描述
            style: 图片风格
            gender: 性别
            age_range: 年龄范围
            reference_images: 参考图片的 base64 编码列表（可选，用于以图生图）

        Returns:
            包含图片URL的字典
        """
        prompt = self._build_asset_image_prompt(description, style, gender, age_range, bool(reference_images))

        return await self.generate_image_with_metadata(prompt, reference_images)

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
