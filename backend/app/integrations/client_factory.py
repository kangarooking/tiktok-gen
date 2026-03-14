"""
Client Factory

Factory for creating integration clients with user or system configurations.
"""
from typing import Dict, Type, Optional, Any
from uuid import UUID
import logging

from app.integrations.base import (
    BaseIntegrationClient,
    LLMClientBase,
    TTSClientBase,
    DigitalHumanClientBase,
    CloudStorageClientBase,
    AIImageClientBase,
)
from app.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ClientFactory:
    """
    Factory for creating integration clients

    Manages client registration and instantiation with configuration.
    """

    # Registry of client classes by category and provider
    _registry: Dict[str, Dict[str, Type[BaseIntegrationClient]]] = {
        "llm": {},
        "tts": {},
        "digital_human": {},
        "cloud_storage": {},
        "ai_image": {},
    }

    @classmethod
    def register(cls, client_class: Type[BaseIntegrationClient]) -> None:
        """
        Register a client class

        Args:
            client_class: The client class to register
        """
        category = client_class.get_category()
        provider = client_class.get_provider_name()

        if category not in cls._registry:
            cls._registry[category] = {}

        cls._registry[category][provider] = client_class
        logger.debug(f"Registered client: {category}/{provider}")

    @classmethod
    def get_registered_providers(cls, category: str) -> list:
        """
        Get list of registered providers for a category

        Args:
            category: Service category

        Returns:
            List of provider names
        """
        return list(cls._registry.get(category, {}).keys())

    @classmethod
    async def create_client(
        cls,
        db,
        user_id: Optional[UUID],
        category: str,
        provider: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None
    ) -> BaseIntegrationClient:
        """
        Create a client instance with configuration

        Priority:
        1. config_override - direct configuration passed in
        2. User's configuration (default or specified provider)
        3. System's configuration (default or specified provider)

        Args:
            db: Database session
            user_id: User ID (can be None for system-only)
            category: Service category (llm, tts, etc.)
            provider: Specific provider (optional, uses default if not specified)
            config_override: Direct configuration to use (bypasses database)

        Returns:
            Configured client instance

        Raises:
            ConfigurationError: If no configuration found
        """
        from app.services.api_config_service import ApiConfigService

        # Use override config if provided
        if config_override:
            if not provider:
                raise ConfigurationError("Provider must be specified when using config_override")

            return cls._create_instance(category, provider, config_override)

        # Get configuration from database
        config_service = ApiConfigService(db)
        config_data = config_service.get_user_or_system_config(
            user_id=user_id,
            category=category,
            provider=provider
        )

        if not config_data:
            raise ConfigurationError(
                f"No configuration found for {category}" +
                (f"/{provider}" if provider else "") +
                ". Please configure your API settings."
            )

        # Determine provider from config if not specified
        if not provider:
            provider = config_service.get_default_provider(user_id, category)
            if not provider:
                raise ConfigurationError(f"No default provider configured for {category}")

        return cls._create_instance(category, provider, config_data)

    @classmethod
    def create_client_from_config(
        cls,
        category: str,
        provider: str,
        config: Dict[str, Any]
    ) -> BaseIntegrationClient:
        """
        Create a client with explicit configuration (synchronous)

        Use this when you have the configuration already and don't need
        to fetch from database.

        Args:
            category: Service category
            provider: Provider name
            config: Configuration dictionary

        Returns:
            Configured client instance
        """
        return cls._create_instance(category, provider, config)

    @classmethod
    def _create_instance(
        cls,
        category: str,
        provider: str,
        config: Dict[str, Any]
    ) -> BaseIntegrationClient:
        """
        Create a client instance

        Args:
            category: Service category
            provider: Provider name
            config: Configuration dictionary

        Returns:
            Client instance

        Raises:
            ConfigurationError: If client class not registered
        """
        # Get client class from registry
        client_class = cls._registry.get(category, {}).get(provider)

        if not client_class:
            # Try to find by provider name across categories
            for cat_providers in cls._registry.values():
                if provider in cat_providers:
                    client_class = cat_providers[provider]
                    break

        if not client_class:
            raise ConfigurationError(
                f"No client registered for {category}/{provider}. "
                "Please ensure the client module is imported."
            )

        # Create and return instance
        return client_class(config)


def register_all_clients():
    """
    Register all available integration clients

    This should be called at application startup.
    """
    # Import all client modules to trigger registration
    try:
        from app.integrations import glm_llm, index_tts, siliconflow_tts, wavespeed_api, ark_seedance, oss_storage, banana_pro
        from app.integrations import custom_openai_ai_image, custom_llm, custom_tts, custom_digital_human
        # These imports will register themselves via decorator or explicit registration
    except ImportError as e:
        logger.warning(f"Some integration modules not available: {e}")

    # Explicitly register known clients
    from app.integrations.glm_llm import GLMLLMClient
    from app.integrations.index_tts import IndexTTSClient
    from app.integrations.siliconflow_tts import SiliconFlowTTSClient
    from app.integrations.wavespeed_api import WaveSpeedClient
    from app.integrations.ark_seedance import ArkSeedanceClient
    from app.integrations.oss_storage import OSSClient
    from app.integrations.banana_pro import BananaProClient
    from app.integrations.custom_openai_ai_image import CustomOpenAIAIImageClient
    from app.integrations.custom_llm import CustomLLMClient
    from app.integrations.custom_tts import CustomTTSClient
    from app.integrations.custom_digital_human import CustomDigitalHumanClient

    ClientFactory.register(GLMLLMClient)
    ClientFactory.register(IndexTTSClient)
    ClientFactory.register(SiliconFlowTTSClient)
    ClientFactory.register(WaveSpeedClient)
    ClientFactory.register(ArkSeedanceClient)
    ClientFactory.register(OSSClient)
    ClientFactory.register(BananaProClient)
    ClientFactory.register(CustomOpenAIAIImageClient)
    ClientFactory.register(CustomLLMClient)
    ClientFactory.register(CustomTTSClient)
    ClientFactory.register(CustomDigitalHumanClient)

    logger.info(f"Registered clients: {ClientFactory._registry}")


# Decorator for automatic registration
def register_client(cls):
    """
    Decorator to automatically register a client class

    Usage:
        @register_client
        class MyClient(BaseIntegrationClient):
            ...
    """
    ClientFactory.register(cls)
    return cls
