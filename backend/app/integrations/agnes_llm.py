"""
Agnes 2.0 Flash LLM integration.
"""
import json
from typing import Dict, List, Optional, Tuple

import httpx

from app.integrations.base import LLMClientBase
from app.integrations.client_factory import register_client


@register_client
class AgnesLLMClient(LLMClientBase):
    """Agnes OpenAI-compatible chat completions client."""

    @classmethod
    def get_provider_name(cls) -> str:
        return "agnes"

    @classmethod
    def get_category(cls) -> str:
        return "llm"

    @classmethod
    def get_required_fields(cls) -> list:
        return ["api_key", "base_url", "model"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = self.get_config_value("api_key")
        self.base_url = self.get_config_value("base_url", "https://apihub.agnes-ai.com/v1").rstrip("/")
        self.model = self.get_config_value("model", "agnes-2.0-flash")
        self.timeout = int(self.get_config_value("timeout", 60))

    async def validate_config(self) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required_fields()
        if not is_valid:
            return is_valid, error
        return True, None

    def _chat_url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    async def chat_completion(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if "top_p" in kwargs and kwargs["top_p"] is not None:
            payload["top_p"] = kwargs["top_p"]
        if "tools" in kwargs and kwargs["tools"]:
            payload["tools"] = kwargs["tools"]
        if "tool_choice" in kwargs and kwargs["tool_choice"]:
            payload["tool_choice"] = kwargs["tool_choice"]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self._chat_url(), json=payload, headers=headers)
            if response.status_code >= 400:
                raise Exception(f"Agnes LLM API error: {response.status_code} - {response.text}")
            data = response.json()

        choices = data.get("choices") or []
        if not choices:
            raise Exception(f"Agnes LLM returned no choices: {data}")
        return choices[0]["message"]["content"]

    async def generate_script(
        self,
        product_name: str,
        product_description: str,
        target_audience: str = "普通消费者",
        tone: str = "轻松活泼",
        duration_seconds: int = 15
    ) -> List[Dict]:
        prompt = f"""请为以下产品创作3个适合 TikTok 的营销短视频脚本。

产品名称：{product_name}
产品描述：{product_description}
目标受众：{target_audience}
风格基调：{tone}
目标时长：{duration_seconds}秒

要求：
1. 开头有强钩子
2. 突出核心卖点
3. 适合口播
4. 包含行动召唤
5. 严格返回 JSON，格式为 {{"scripts":[{{"content":"...","estimated_seconds":15,"word_count":80}}]}}
"""
        response = await self.chat_completion(
            messages=[
                {"role": "system", "content": "你是专业的 TikTok 营销短视频脚本专家。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=2000,
        )
        return self._parse_scripts(response)

    def _parse_scripts(self, response: str) -> List[Dict]:
        text = response.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                scripts = data.get("scripts", [])
                if scripts:
                    return scripts
        except json.JSONDecodeError:
            pass

        word_count = len(text)
        return [{
            "content": text,
            "estimated_seconds": max(5, word_count // 7),
            "word_count": word_count,
        }]
