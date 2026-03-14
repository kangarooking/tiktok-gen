"""
Custom OpenAI-compatible LLM 服务集成

支持任何兼容 OpenAI Chat Completions API 的 LLM 服务
"""
import httpx
from typing import Optional, Dict, Tuple, List
from app.integrations.base import LLMClientBase
from app.integrations.client_factory import register_client


@register_client
class CustomLLMClient(LLMClientBase):
    """Custom OpenAI-compatible LLM 客户端"""

    @classmethod
    def get_provider_name(cls) -> str:
        return "custom"

    @classmethod
    def get_category(cls) -> str:
        return "llm"

    @classmethod
    def get_required_fields(cls) -> list:
        return ["api_key", "base_url"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = self.get_config_value("api_key")
        self.base_url = self.get_config_value("base_url", "").rstrip("/")
        self.model = self.get_config_value("model") or "gpt-4"
        self.timeout = self.get_config_value("timeout") or 60

    async def validate_config(self) -> Tuple[bool, Optional[str]]:
        """Validate the configuration"""
        is_valid, error = self.validate_required_fields()
        if not is_valid:
            return is_valid, error
        if not self.base_url:
            return False, "base_url is required"
        return True, None

    async def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        Chat completion

        Args:
            messages: List of message dicts with role and content
            temperature: Sampling temperature
            max_tokens: Max tokens to generate

        Returns:
            Generated text
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
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
                raise Exception(f"API error: {response.status_code} - {response.text}")

            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def chat_completion(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Compatibility method required by LLMClientBase."""
        return await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def generate_script(
        self,
        product_name: str,
        product_description: str,
        target_audience: str = "普通消费者",
        tone: str = "轻松活泼",
        duration_seconds: int = 15
    ) -> List[Dict]:
        """
        生成营销脚本

        Args:
            product_name: 产品名称
            product_description: 产品描述
            target_audience: 目标受众
            tone: 风格基调
            duration_seconds: 目标时长

        Returns:
            生成的脚本列表
        """
        system_prompt = """你是一个专业的短视频脚本撰写专家。你需要根据产品信息，创作适合TikTok/抖音等短视频平台的营销脚本。

要求：
1. 脚本要简洁有力，适合口播
2. 包含吸引眼球的开头
3. 突出产品核心卖点
4. 有明确的行动号召
5. 语言要口语化，有感染力

请直接返回JSON格式的脚本数组，每个脚本包含：
- title: 脚本标题
- content: 脚本内容
- word_count: 字数
- estimated_seconds: 预估时长（秒）"""

        user_prompt = f"""请为以下产品创作3个不同风格的短视频营销脚本：

产品名称：{product_name}
产品描述：{product_description}
目标受众：{target_audience}
风格基调：{tone}
目标时长：{duration_seconds}秒左右

请返回JSON数组格式。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = await self.chat(messages, temperature=0.8, max_tokens=2000)

        # Parse JSON response
        import json
        try:
            # Try to extract JSON from the response
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                scripts = json.loads(json_str)
            else:
                # Fallback: create a single script from the response
                scripts = [{
                    "title": f"{product_name}营销脚本",
                    "content": response,
                    "word_count": len(response),
                    "estimated_seconds": len(response) // 7
                }]
        except json.JSONDecodeError:
            scripts = [{
                "title": f"{product_name}营销脚本",
                "content": response,
                "word_count": len(response),
                "estimated_seconds": len(response) // 7
            }]

        return scripts
