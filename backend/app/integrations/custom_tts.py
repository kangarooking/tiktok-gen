"""
Custom TTS 服务集成

支持自定义 TTS API
"""
import httpx
from typing import Optional, Dict, Tuple
from app.integrations.base import TTSClientBase
from app.integrations.client_factory import register_client


@register_client
class CustomTTSClient(TTSClientBase):
    """Custom TTS API 客户端"""

    @classmethod
    def get_provider_name(cls) -> str:
        return "custom"

    @classmethod
    def get_category(cls) -> str:
        return "tts"

    @classmethod
    def get_required_fields(cls) -> list:
        return ["base_url"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = self.get_config_value("api_key")
        self.base_url = self.get_config_value("base_url", "").rstrip("/")
        self.model = self.get_config_value("model")
        self.timeout = self.get_config_value("timeout") or 120

    async def validate_config(self) -> Tuple[bool, Optional[str]]:
        """Validate the configuration"""
        is_valid, error = self.validate_required_fields()
        if not is_valid:
            return is_valid, error
        if not self.base_url:
            return False, "base_url is required"
        return True, None

    async def generate_audio(
        self,
        text: str,
        voice_file_url: Optional[str] = None,
        emotion: str = "neutral",
        **kwargs
    ) -> str:
        """
        Generate audio from text

        Args:
            text: Text to convert to speech
            voice_file_url: Reference voice file URL (for voice cloning)
            emotion: Emotion style

        Returns:
            URL of the generated audio file
        """
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "text": text,
            "voice_url": voice_file_url,
            "emotion": emotion
        }
        if self.model:
            payload["model"] = self.model

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/tts",
                json=payload,
                headers=headers
            )

            if response.status_code != 200:
                raise Exception(f"TTS API error: {response.status_code} - {response.text}")

            data = response.json()

            # Try different response formats
            if "audio_url" in data:
                return data["audio_url"]
            elif "url" in data:
                return data["url"]
            elif "data" in data and isinstance(data["data"], dict):
                return data["data"].get("url") or data["data"].get("audio_url")
            else:
                raise Exception(f"Unexpected TTS response format: {data}")

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        **kwargs
    ) -> bytes:
        """Compatibility method required by TTSClientBase."""
        audio_url = await self.generate_audio(
            text=text,
            voice_file_url=voice,
            emotion=kwargs.get("emotion", "neutral"),
            **kwargs,
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(audio_url)
            response.raise_for_status()
            return response.content
