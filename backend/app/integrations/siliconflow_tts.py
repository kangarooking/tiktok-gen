"""
SiliconFlow TTS integration.
"""
from typing import Dict, Optional, Tuple, List
import re
import os
import shutil
import subprocess
import tempfile

import httpx

from app.config import settings
from app.integrations.base import TTSClientBase


class SiliconFlowTTSClient(TTSClientBase):
    """SiliconFlow /audio/speech client."""

    _DEFAULT_EMOTION_TEXT = {
        "happy": "请使用开心、明亮、上扬的语气。",
        "excited": "请使用兴奋、有感染力的语气。",
        "professional": "请使用专业、清晰、稳定的语气。",
        "gentle": "请使用温柔、舒缓的语气。",
        "serious": "请使用严肃、沉稳的语气。",
    }
    _VOICE_URI_CACHE: Dict[str, str] = {}
    _DEFAULT_REF_TEXT = "这是一段用于建立音色特征的参考音频文本。"
    _SUPPORTED_UPLOAD_EXTS = {"wav", "mp3", "pcm", "opus"}

    @staticmethod
    def _sanitize_custom_name(name: Optional[str]) -> str:
        raw = (name or "voice_ref").strip()
        # SiliconFlow requires only letters/digits/_/-, max 64 chars.
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", raw)
        cleaned = re.sub(r"_+", "_", cleaned).strip("_-")
        if not cleaned:
            cleaned = "voice_ref"
        return cleaned[:64]

    def _try_convert_to_wav(self, audio_bytes: bytes, src_ext: str) -> Optional[bytes]:
        """
        Best-effort local conversion to wav for unsupported formats (e.g. m4a/mp4).
        Uses macOS built-in `afconvert` when available.
        """
        afconvert_bin = shutil.which("afconvert")
        if not afconvert_bin:
            return None

        src_path = ""
        dst_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{src_ext or 'audio'}") as src_file:
                src_file.write(audio_bytes)
                src_path = src_file.name
            dst_path = f"{src_path}.wav"

            # 16-bit PCM WAV at 24kHz, good enough for voice cloning reference.
            cmd = [afconvert_bin, "-f", "WAVE", "-d", "LEI16@24000", src_path, dst_path]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                self.logger.warning(
                    "afconvert failed while converting reference audio: %s",
                    (proc.stderr or proc.stdout or "").strip()
                )
                return None

            with open(dst_path, "rb") as f:
                return f.read()
        except Exception as e:
            self.logger.warning("reference audio conversion failed: %s", e)
            return None
        finally:
            for p in (src_path, dst_path):
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

    @classmethod
    def get_provider_name(cls) -> str:
        return "siliconflow_tts"

    @classmethod
    def get_category(cls) -> str:
        return "tts"

    @classmethod
    def get_required_fields(cls) -> list:
        return ["api_key", "base_url", "model"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = self.get_config_value("api_key") or settings.SILICONFLOW_API_KEY
        self.base_url = (self.get_config_value("base_url") or settings.SILICONFLOW_BASE_URL).rstrip("/")
        self.model = self.get_config_value("model") or settings.SILICONFLOW_TTS_MODEL
        self.voice = self.get_config_value("voice") or settings.SILICONFLOW_TTS_VOICE or None
        self.response_format = self.get_config_value("response_format", "mp3")
        self.speed = float(self.get_config_value("speed", 1.0))
        self.gain = float(self.get_config_value("gain", 0.0))
        self.sample_rate = int(self.get_config_value("sample_rate", 32000))
        self.timeout = int(self.get_config_value("timeout") or settings.SILICONFLOW_TTS_TIMEOUT)

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

    @staticmethod
    async def list_audio_models(
        api_key: str,
        base_url: str = "https://api.siliconflow.cn/v1",
        timeout: int = 20,
    ) -> List[Dict]:
        """Fetch latest audio model list from SiliconFlow."""
        if not api_key:
            raise ValueError("api_key is required")

        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                f"{base_url.rstrip('/')}/models",
                params={"type": "audio"},
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        raw_items = data.get("data", []) if isinstance(data, dict) else []
        models: List[Dict] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            model_id = item.get("id") or item.get("model")
            if not model_id:
                continue
            models.append(
                {
                    "id": str(model_id),
                    "label": str(item.get("owned_by") or item.get("name") or model_id),
                }
            )

        # De-duplicate by id while preserving order.
        seen = set()
        deduped = []
        for m in models:
            if m["id"] in seen:
                continue
            seen.add(m["id"])
            deduped.append(m)
        return deduped

    def _build_input_text(
        self,
        text: str,
        emotion: str = "professional",
        emotion_mode: str = "preset",
        emotion_text: Optional[str] = None,
    ) -> str:
        mode = (emotion_mode or "preset").lower()
        if mode == "text_ref" and emotion_text:
            return f"{emotion_text}\n\n{text}"
        if mode in {"vector", "audio_ref"}:
            # SiliconFlow public speech API does not expose unified 8D emotion vector/audio-ref params.
            # Keep text intact to avoid injecting unreliable mappings.
            return text
        hint = self._DEFAULT_EMOTION_TEXT.get((emotion or "").lower())
        if hint:
            return f"{hint}\n\n{text}"
        return text

    def _build_payload(
        self,
        text: str,
        voice: Optional[str] = None,
        emotion: str = "professional",
        emotion_mode: str = "preset",
        emotion_text: Optional[str] = None,
    ) -> Dict:
        payload: Dict = {
            "model": self.model,
            "input": self._build_input_text(
                text=text,
                emotion=emotion,
                emotion_mode=emotion_mode,
                emotion_text=emotion_text,
            ),
            "response_format": self.response_format,
            "speed": self.speed,
            "gain": self.gain,
            "sample_rate": self.sample_rate,
        }

        selected_voice = voice or self.voice
        if selected_voice:
            payload["voice"] = selected_voice

        return payload

    async def _upload_reference_voice_and_get_uri(
        self,
        voice_file_url: str,
        model: str,
        custom_name: Optional[str] = None,
        reference_text: Optional[str] = None,
    ) -> str:
        if voice_file_url in self._VOICE_URI_CACHE:
            return self._VOICE_URI_CACHE[voice_file_url]

        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            file_resp = await client.get(voice_file_url)
            file_resp.raise_for_status()
            audio_bytes = file_resp.content
            content_type = file_resp.headers.get("content-type", "audio/mpeg")
            ext = "mp3"
            if "/" in content_type:
                maybe = content_type.split("/")[-1].split(";")[0].strip().lower()
                if maybe:
                    ext = maybe
            # Normalize common aliases/unsupported ext names.
            if ext in {"mpeg", "mpga"}:
                ext = "mp3"
            if ext in {"x-wav"}:
                ext = "wav"
            if ext in {"ogg"}:
                ext = "opus"
            # SiliconFlow only accepts wav/mp3/pcm/opus on upload.
            if ext not in self._SUPPORTED_UPLOAD_EXTS:
                converted = self._try_convert_to_wav(audio_bytes=audio_bytes, src_ext=ext)
                if converted:
                    audio_bytes = converted
                    ext = "wav"
                    content_type = "audio/wav"
                else:
                    # Fallback: some providers only validate metadata extension/content-type.
                    ext = "mp3"
                    content_type = "audio/mpeg"

            safe_name = self._sanitize_custom_name(custom_name)
            filename = f"{safe_name}.{ext}"
            form_data = {
                "model": model,
                "customName": safe_name,
                "text": reference_text or self._DEFAULT_REF_TEXT,
            }
            files = {"file": (filename, audio_bytes, content_type)}

            upload_resp = await client.post(
                f"{self.base_url}/uploads/audio/voice",
                data=form_data,
                files=files,
                headers=headers,
            )
            if upload_resp.status_code >= 400:
                detail = upload_resp.text.strip()
                try:
                    err_json = upload_resp.json()
                except Exception:
                    err_json = {}
                err_code = err_json.get("code")
                # Final user-facing hint for unsupported source format.
                if err_code == 20082:
                    raise ValueError(
                        "SiliconFlow voice upload failed: 当前音频格式不被支持，请将音色转换为 mp3/wav/pcm/opus 后重试。"
                    )
                raise ValueError(f"SiliconFlow voice upload failed ({upload_resp.status_code}): {detail}")

            result = upload_resp.json()
            uri = result.get("uri")
            if not uri:
                raise ValueError(f"SiliconFlow voice upload returned no uri: {result}")

            self._VOICE_URI_CACHE[voice_file_url] = uri
            return uri

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        **kwargs
    ) -> bytes:
        voice_file_url = kwargs.get("voice_file_url")
        selected_voice = voice or self.voice

        if isinstance(selected_voice, str) and selected_voice.startswith("http"):
            voice_file_url = selected_voice
            selected_voice = None

        # SiliconFlow /audio/speech expects a built-in voice id or uploaded speech uri.
        # If caller passes a regular audio URL (our voice asset), auto-upload it first.
        if not selected_voice and isinstance(voice_file_url, str) and voice_file_url:
            selected_voice = await self._upload_reference_voice_and_get_uri(
                voice_file_url=voice_file_url,
                model=self.model,
                custom_name=kwargs.get("voice_name"),
                reference_text=kwargs.get("voice_reference_text"),
            )

        payload = self._build_payload(
            text=text,
            voice=selected_voice,
            emotion=kwargs.get("emotion", "professional"),
            emotion_mode=kwargs.get("emotion_mode", "preset"),
            emotion_text=kwargs.get("emotion_text"),
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/audio/speech",
                json=payload,
                headers=headers,
            )
            if response.status_code >= 400:
                detail = response.text.strip()
                raise ValueError(f"SiliconFlow speech failed ({response.status_code}): {detail}")
            return response.content

    async def generate_audio(
        self,
        text: str,
        voice_file_url: Optional[str] = None,
        emotion: str = "professional",
        emotion_mode: str = "preset",
        emotion_vector: Optional[list] = None,
        emotion_text: Optional[str] = None,
        emotion_alpha: Optional[float] = None,
        emotion_audio_url: Optional[str] = None,
    ) -> str:
        raise NotImplementedError(
            "siliconflow_tts returns audio bytes from /audio/speech. "
            "Call synthesize() and upload bytes to your storage to get a URL."
        )
