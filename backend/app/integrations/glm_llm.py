"""
GLM-4.7 LLM API集成
"""
import httpx
from typing import List, Dict, Optional, Tuple
from app.config import settings
from app.integrations.base import LLMClientBase


class GLMLLMClient(LLMClientBase):
    """GLM-4.7 API客户端"""

    @classmethod
    def get_provider_name(cls) -> str:
        return "glm"

    @classmethod
    def get_category(cls) -> str:
        return "llm"

    @classmethod
    def get_required_fields(cls) -> list:
        return ["api_key", "base_url", "model"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        # Use config values or fall back to settings
        self.api_key = self.get_config_value("api_key") or settings.GLM_API_KEY
        self.base_url = self.get_config_value("base_url") or settings.GLM_API_URL
        self.model = self.get_config_value("model") or settings.GLM_MODEL
        self.timeout = self.get_config_value("timeout") or settings.GLM_TIMEOUT

    async def validate_config(self) -> Tuple[bool, Optional[str]]:
        """Validate the configuration by making a simple API call"""
        is_valid, error = self.validate_required_fields()
        if not is_valid:
            return is_valid, error

        try:
            # Try a simple API call
            await self.chat_completion(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True, None
        except Exception as e:
            return False, str(e)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False
    ) -> str:
        """
        调用GLM-4.7 API进行对话补全

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数
            stream: 是否流式输出

        Returns:
            模型响应文本

        Raises:
            Exception: API调用失败
        """
        import logging
        logger = logging.getLogger(__name__)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            try:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()

                result = response.json()

                # 提取内容
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    logger.info(f"GLM API response: {content[:200]}...")
                    return content
                else:
                    logger.error(f"GLM API返回格式异常: {result}")
                    raise Exception(f"GLM API返回格式异常: {result}")
            except httpx.HTTPStatusError as e:
                logger.error(f"GLM API HTTP error: {e.response.status_code} - {e.response.text}")
                raise Exception(f"GLM API调用失败: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"GLM API调用异常: {str(e)}")
                raise

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
            脚本列表 [{"content": "...", "estimated_seconds": 12, "word_count": 85}]
        """
        prompt = f"""请为以下产品创作3个吸引人的TikTok营销短视频脚本：

产品名称: {product_name}
产品描述: {product_description}
目标受众: {target_audience}
风格基调: {tone}
目标时长: {duration_seconds}秒

要求:
1. 开头必须有吸引眼球的钩子
2. 突出产品核心卖点
3. 语言口语化、有节奏感
4. 包含明确的行动召唤(CTA)
5. 每个脚本单独一段

请以JSON格式返回，格式如下:
{{
    "scripts": [
        {{"content": "脚本内容", "estimated_seconds": 12, "word_count": 85}},
        ...
    ]
}}"""

        response = await self.chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "你是一位专业的短视频营销脚本创作专家，擅长创作吸引人的TikTok风格营销脚本。"
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=2000
        )

        # 解析脚本
        return self._parse_scripts(response)

    def _parse_scripts(self, response: str) -> List[Dict]:
        """
        解析LLM返回的脚本

        Args:
            response: LLM返回的文本

        Returns:
            脚本列表
        """
        import json
        import re
        # 去除markdown代码块标记（如果存在）
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        # 尝试提取JSON部分
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
                scripts = data.get("scripts", [])
                if scripts:
                    self.logger.info(f"Successfully parsed {len(scripts)} scripts")
                    return scripts
                else:
                    self.logger.warning("No scripts found in JSON response")
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON: {e}")

        # 最后的fallback：返回原始响应作为单个脚本
        self.logger.info(f"Using raw response as script ({len(response)} chars)")
        word_count = len(response)
        estimated_seconds = max(5, word_count // 7)
        return [{
            "content": response,
            "estimated_seconds": estimated_seconds,
            "word_count": word_count
        }]
