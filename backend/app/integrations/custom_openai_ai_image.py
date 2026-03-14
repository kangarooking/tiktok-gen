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
        style: str = "写实风格",
        gender: str = "女性",
        age_range: str = "20-30岁",
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
        # 构建详细的提示词
        if reference_images:
            # 以图生图模式
            prompt = f"""请参考上传的图片，生成一个{gender}的{style}头像图片。

人物特征：
- 年龄：{age_range}
- 性别：{gender}
- 描述：{description}

要求：
1. 保持参考图片的人物特征和风格
2. 人物面部清晰，五官端正
3. 光线均匀，背景简洁
4. 适合用作数字人形象
5. 正面或略带角度的视角
6. 表情自然，有亲和力

请只生成图片，不要添加任何文字说明。"""
        else:
            # 文生图模式
            prompt = f"""请生成一个{gender}的{style}头像图片。

人物特征：
- 年龄：{age_range}
- 性别：{gender}
- 描述：{description}

要求：
1. 人物面部清晰，五官端正
2. 光线均匀，背景简洁
3. 适合用作数字人形象
4. 正面或略带角度的视角
5. 表情自然，有亲和力

请只生成图片，不要添加任何文字说明。"""

        return await self.generate_image_with_metadata(prompt, reference_images)
