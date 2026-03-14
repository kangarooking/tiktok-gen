"""
Index TTS (302.AI Task API) integration.
"""
import asyncio
import httpx
from typing import Dict, Optional, Tuple, List

from app.config import settings
from app.integrations.base import TTSClientBase


class IndexTTSClient(TTSClientBase):
    """302.AI hosted Index TTS v2 client"""

    _PRESET_EMOTION_VECTORS: Dict[str, List[float]] = {
        "happy": [0.90, 0.00, 0.00, 0.00, 0.00, 0.00, 0.08, 0.02],
        "excited": [0.82, 0.04, 0.00, 0.02, 0.00, 0.00, 0.12, 0.00],
        "professional": [0.05, 0.00, 0.00, 0.00, 0.00, 0.00, 0.05, 0.90],
        "gentle": [0.10, 0.00, 0.06, 0.00, 0.00, 0.12, 0.00, 0.72],
        "serious": [0.00, 0.12, 0.08, 0.02, 0.00, 0.18, 0.00, 0.60],
    }

    @classmethod
    def get_provider_name(cls) -> str:
        return "index_tts"

    @classmethod
    def get_category(cls) -> str:
        return "tts"

    @classmethod
    def get_required_fields(cls) -> list:
        return ["api_key", "base_url"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = self.get_config_value("api_key") or settings.INDEX_TTS_API_KEY
        self.base_url = (self.get_config_value("base_url") or settings.INDEX_TTS_BASE_URL).rstrip("/")
        self.timeout = int(self.get_config_value("timeout") or settings.INDEX_TTS_TIMEOUT)

    async def validate_config(self) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required_fields()
        if not is_valid:
            return is_valid, error

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(self.base_url)
                if response.status_code >= 500:
                    return False, f"TTS base URL not reachable: {response.status_code}"
        except Exception as e:
            return False, f"Cannot reach TTS service: {e}"

        return True, None

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        **kwargs
    ) -> bytes:
        audio_url = await self.generate_audio(
            text=text,
            voice_file_url=voice,
            **kwargs,
        )
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(audio_url)
            response.raise_for_status()
            return response.content

    async def generate_audio(
        self,
        text: str,
        voice_file_url: str,
        emotion: str = "professional",
        emotion_mode: str = "preset",
        emotion_vector: Optional[List[float]] = None,
        emotion_text: Optional[str] = None,
        emotion_alpha: Optional[float] = None,
        emotion_audio_url: Optional[str] = None,
    ) -> str:
        if not voice_file_url:
            raise ValueError("voice_file_url is required")

        task_id = await self._create_task(
            text=text,
            voice_file_url=voice_file_url,
            emotion=emotion,
            emotion_mode=emotion_mode,
            emotion_vector=emotion_vector,
            emotion_text=emotion_text,
            emotion_alpha=emotion_alpha,
            emotion_audio_url=emotion_audio_url,
        )

        return await self._wait_for_audio_url(task_id)

    async def _create_task(
        self,
        text: str,
        voice_file_url: str,
        emotion: str,
        emotion_mode: str,
        emotion_vector: Optional[List[float]],
        emotion_text: Optional[str],
        emotion_alpha: Optional[float],
        emotion_audio_url: Optional[str],
    ) -> str:
        payload: Dict = {
            "text": text,
            "speaker_audio_url": voice_file_url,
        }

        mode = (emotion_mode or "preset").lower()
        if mode == "vector" and emotion_vector:
            if len(emotion_vector) != 8:
                raise ValueError("emotion_vector must have exactly 8 values")
            payload["emotion_vector"] = [float(v) for v in emotion_vector]
        elif mode == "text_ref" and emotion_text:
            payload["use_emotion_text"] = True
            payload["emotion_text"] = emotion_text
        elif mode == "audio_ref" and emotion_audio_url:
            payload["emotion_audio_url"] = emotion_audio_url
            payload["emotion_alpha"] = float(emotion_alpha if emotion_alpha is not None else 0.6)
        else:
            preset = self._PRESET_EMOTION_VECTORS.get((emotion or "").lower())
            if preset:
                payload["emotion_vector"] = preset

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/302/index_tts2/task",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            result = response.json()

        task_id = result.get("task_id")
        if not task_id:
            raise Exception(f"Unexpected TTS create response: {result}")
        return task_id

    async def _wait_for_audio_url(self, task_id: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        max_attempts = max(10, min(self.timeout, 300))
        async with httpx.AsyncClient(timeout=30) as client:
            for _ in range(max_attempts):
                response = await client.get(
                    f"{self.base_url}/302/index_tts2/task",
                    params={"task_id": task_id},
                    headers=headers,
                )
                response.raise_for_status()
                result = response.json()

                state = str(result.get("state", "")).lower()
                audio_url = result.get("audio_url")

                if audio_url and state in {"success", "succeeded", "completed", "done"}:
                    return audio_url

                if state in {"failed", "error", "cancelled"}:
                    error_msg = result.get("error", {}).get("message") if isinstance(result.get("error"), dict) else result.get("error")
                    raise Exception(error_msg or f"TTS task failed: {result}")

                if audio_url and not state:
                    return audio_url

                await asyncio.sleep(1)

        raise TimeoutError(f"TTS task timeout: {task_id}")
