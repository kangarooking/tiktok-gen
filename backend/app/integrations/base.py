"""
Base Integration Client

Abstract base class for all third-party integration clients.
Provides common interface for configuration-based instantiation.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
import logging


class BaseIntegrationClient(ABC):
    """
    Abstract base class for integration clients

    All integration clients should inherit from this class and implement
    the required abstract methods.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the client with configuration

        Args:
            config: Configuration dictionary from user or system settings
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @classmethod
    @abstractmethod
    def get_provider_name(cls) -> str:
        """
        Get the provider identifier

        Returns:
            Provider name (e.g., 'openai', 'aliyun_oss')
        """
        pass

    @classmethod
    @abstractmethod
    def get_category(cls) -> str:
        """
        Get the service category

        Returns:
            Category name (e.g., 'llm', 'cloud_storage', 'tts', 'digital_human', 'ai_image')
        """
        pass

    @classmethod
    def get_required_fields(cls) -> list:
        """
        Get list of required configuration fields

        Override this method to specify which fields are required.

        Returns:
            List of field names
        """
        return []

    @abstractmethod
    async def validate_config(self) -> Tuple[bool, Optional[str]]:
        """
        Validate the current configuration

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def validate_required_fields(self) -> Tuple[bool, Optional[str]]:
        """
        Validate that all required fields are present

        Returns:
            Tuple of (is_valid, error_message)
        """
        required = self.get_required_fields()
        missing = []

        for field in required:
            if not self.get_config_value(field):
                missing.append(field)

        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"

        return True, None


class LLMClientBase(BaseIntegrationClient):
    """Base class for LLM clients"""

    @classmethod
    def get_category(cls) -> str:
        return "llm"

    @abstractmethod
    async def chat_completion(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate chat completion

        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        pass


class TTSClientBase(BaseIntegrationClient):
    """Base class for TTS clients"""

    @classmethod
    def get_category(cls) -> str:
        return "tts"

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        **kwargs
    ) -> bytes:
        """
        Synthesize speech from text

        Args:
            text: Text to synthesize
            voice: Voice identifier

        Returns:
            Audio data as bytes
        """
        pass


class DigitalHumanClientBase(BaseIntegrationClient):
    """Base class for digital human video generation clients"""

    @classmethod
    def get_category(cls) -> str:
        return "digital_human"

    @abstractmethod
    async def generate_video(
        self,
        avatar_image_url: str,
        audio_url: str,
        **kwargs
    ) -> str:
        """
        Generate a digital human video

        Args:
            avatar_image_url: URL of the avatar image
            audio_url: URL of the audio file

        Returns:
            URL of the generated video
        """
        pass


class CloudStorageClientBase(BaseIntegrationClient):
    """Base class for cloud storage clients"""

    @classmethod
    def get_category(cls) -> str:
        return "cloud_storage"

    @abstractmethod
    async def upload_file(
        self,
        file_data: bytes,
        key: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload a file to cloud storage

        Args:
            file_data: File content as bytes
            key: Storage key/path
            content_type: MIME type

        Returns:
            Public URL of the uploaded file
        """
        pass

    @abstractmethod
    async def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600
    ) -> str:
        """
        Get a presigned URL for a file

        Args:
            key: Storage key/path
            expires_in: URL expiration time in seconds

        Returns:
            Presigned URL
        """
        pass


class AIImageClientBase(BaseIntegrationClient):
    """Base class for AI image generation clients"""

    @classmethod
    def get_category(cls) -> str:
        return "ai_image"

    @abstractmethod
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
        pass
