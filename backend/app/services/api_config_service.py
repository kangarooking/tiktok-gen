"""
API Configuration Service

Handles CRUD operations for user API configurations with encryption.
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.user_api_config import UserApiConfig
from app.core.encryption import encrypt_config, decrypt_config, mask_config
from app.core.provider_constants import (
    ApiCategory,
    get_provider_definition,
    get_providers_by_category,
    provider_to_dict,
    get_category_display_name,
    get_category_icon,
)
from app.core.exceptions import ValidationError, NotFoundError, ForbiddenError

logger = logging.getLogger(__name__)


class ApiConfigService:
    """Service for managing user API configurations"""

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # Provider Information
    # ============================================================

    def get_all_providers(self) -> Dict[str, Any]:
        """
        Get all available providers grouped by category

        Returns:
            Dictionary with categories and their providers
        """
        categories = []
        for category in ApiCategory:
            providers = self._get_supported_providers(category)
            category_data = {
                "category": category.value,
                "display_name": get_category_display_name(category),
                "icon": get_category_icon(category),
                "providers": [provider_to_dict(p) for p in providers]
            }
            categories.append(category_data)

        return {"categories": categories}

    def get_providers_for_category(self, category: str) -> Dict[str, Any]:
        """
        Get all providers for a specific category

        Args:
            category: Category name

        Returns:
            Dictionary with category info and providers
        """
        try:
            cat = ApiCategory(category)
        except ValueError:
            raise ValidationError(f"Invalid category: {category}")

        providers = self._get_supported_providers(cat)
        return {
            "category": cat.value,
            "display_name": get_category_display_name(cat),
            "icon": get_category_icon(cat),
            "providers": [provider_to_dict(p) for p in providers]
        }

    # ============================================================
    # CRUD Operations
    # ============================================================

    async def create_config(
        self,
        user_id: UUID,
        category: str,
        provider: str,
        config_data: Dict[str, Any],
        display_name: Optional[str] = None,
        set_as_default: bool = False
    ) -> UserApiConfig:
        """
        Create a new API configuration

        Args:
            user_id: User ID
            category: Configuration category
            provider: Provider name
            config_data: Configuration data (will be encrypted)
            display_name: User-friendly name
            set_as_default: Whether to set as default

        Returns:
            Created configuration
        """
        # Validate category and provider
        provider_def = get_provider_definition(provider, category)
        if not provider_def:
            raise ValidationError(f"Unknown provider: {provider}")

        if provider_def.category.value != category:
            raise ValidationError(
                f"Provider {provider} does not belong to category {category}"
            )

        # Validate required fields
        self._validate_config_data(provider_def.fields, config_data)

        # Check if config already exists for this user/category/provider
        existing = self.db.query(UserApiConfig).filter(
            UserApiConfig.user_id == user_id,
            UserApiConfig.category == category,
            UserApiConfig.provider == provider
        ).first()

        if existing:
            raise ValidationError(
                f"Configuration already exists for {provider} in {category}. "
                "Please update the existing configuration instead."
            )

        # Encrypt configuration data
        encrypted_data = encrypt_config(config_data)

        # If this is the first active config in this category, make it default
        if not set_as_default:
            has_default = self.db.query(UserApiConfig).filter(
                UserApiConfig.user_id == user_id,
                UserApiConfig.category == category,
                UserApiConfig.is_active == True,
                UserApiConfig.is_default == True
            ).first()
            if not has_default:
                set_as_default = True

        # If set_as_default, unset other defaults in this category
        if set_as_default:
            self._unset_defaults(user_id, category)

        # Create config
        config = UserApiConfig(
            user_id=user_id,
            category=category,
            provider=provider,
            config_data=encrypted_data,
            display_name=display_name or provider_def.display_name,
            is_default=set_as_default,
            is_system=False,
        )

        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)

        logger.info(f"Created API config {config.id} for user {user_id}: {category}/{provider}")

        return config

    async def update_config(
        self,
        config_id: UUID,
        user_id: UUID,
        display_name: Optional[str] = None,
        config_data: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None
    ) -> UserApiConfig:
        """
        Update an existing configuration

        Args:
            config_id: Configuration ID
            user_id: User ID (for ownership check)
            display_name: New display name
            config_data: New configuration data
            is_active: New active status

        Returns:
            Updated configuration
        """
        config = self._get_user_config(config_id, user_id)

        if config.is_system:
            raise ForbiddenError("Cannot modify system-level configuration")

        if display_name is not None:
            config.display_name = display_name

        if is_active is not None:
            config.is_active = is_active

        if config_data is not None:
            # Merge with existing values so partial updates don't drop fields.
            try:
                existing_data = decrypt_config(config.config_data)
            except Exception:
                existing_data = {}
            merged_data = dict(existing_data)
            merged_data.update(config_data)

            # Validate new config data
            provider_def = get_provider_definition(config.provider, config.category)
            if provider_def:
                sensitive_fields = [f.name for f in provider_def.fields if f.sensitive]
                for field_name in sensitive_fields:
                    new_value = merged_data.get(field_name)
                    # Settings UI returns masked values (e.g. "sk-********abcd");
                    # keep original secret instead of re-encrypting the masked text.
                    if isinstance(new_value, str) and "*" in new_value:
                        existing_value = existing_data.get(field_name)
                        if existing_value:
                            merged_data[field_name] = existing_value

                self._validate_config_data(provider_def.fields, merged_data)

            # Encrypt and store
            config.config_data = encrypt_config(merged_data)
            config.is_validated = False
            config.validation_error = None

        config.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(config)

        logger.info(f"Updated API config {config_id}")

        return config

    async def delete_config(self, config_id: UUID, user_id: UUID) -> None:
        """
        Delete a configuration

        Args:
            config_id: Configuration ID
            user_id: User ID (for ownership check)
        """
        config = self._get_user_config(config_id, user_id)

        if config.is_system:
            raise ForbiddenError("Cannot delete system-level configuration")

        self.db.delete(config)
        self.db.commit()

        logger.info(f"Deleted API config {config_id}")

    async def get_config(
        self,
        config_id: UUID,
        user_id: UUID,
        include_decrypted: bool = False
    ) -> Dict[str, Any]:
        """
        Get a configuration by ID

        Args:
            config_id: Configuration ID
            user_id: User ID
            include_decrypted: Whether to include decrypted data

        Returns:
            Configuration dictionary
        """
        config = self._get_user_config(config_id, user_id, include_system=True)
        return self._serialize_config(config, include_decrypted)

    async def get_decrypted_config_for_runtime(
        self,
        config_id: UUID,
        user_id: UUID
    ) -> Tuple[UserApiConfig, Dict[str, Any]]:
        """Get a user-owned config and decrypted raw data for runtime validation."""
        config = self._get_user_config(config_id, user_id)
        return config, decrypt_config(config.config_data)

    async def list_configs(
        self,
        user_id: UUID,
        category: Optional[str] = None,
        include_system: bool = True,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        List configurations for a user

        Args:
            user_id: User ID
            category: Filter by category (optional)
            include_system: Include system-level configs
            page: Page number
            page_size: Page size

        Returns:
            Dictionary with list and pagination
        """
        query = self.db.query(UserApiConfig).filter(
            or_(
                UserApiConfig.user_id == user_id,
                UserApiConfig.is_system == True if include_system else False
            )
        )

        if category:
            query = query.filter(UserApiConfig.category == category)

        # Order by category, then by is_default
        query = query.order_by(
            UserApiConfig.category,
            UserApiConfig.is_default.desc(),
            UserApiConfig.created_at.desc()
        )

        # Count total
        total = query.count()

        # Paginate
        configs = query.offset((page - 1) * page_size).limit(page_size).all()

        return {
            "list": [self._serialize_config(c) for c in configs],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        }

    async def get_configs_by_category(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get configurations grouped by category

        Args:
            user_id: User ID

        Returns:
            List of category dictionaries with configs
        """
        result = []

        for category in ApiCategory:
            # Get user configs for this category
            user_configs = self.db.query(UserApiConfig).filter(
                UserApiConfig.user_id == user_id,
                UserApiConfig.category == category.value,
                UserApiConfig.is_active == True
            ).all()

            # Get system configs for this category (if no user config)
            system_configs = []
            if not user_configs:
                system_configs = self.db.query(UserApiConfig).filter(
                    UserApiConfig.is_system == True,
                    UserApiConfig.category == category.value,
                    UserApiConfig.is_active == True
                ).all()

            all_configs = user_configs or system_configs

            # Find default
            default_config = next(
                (c for c in all_configs if c.is_default),
                all_configs[0] if all_configs else None
            )

            category_data = {
                "category": category.value,
                "display_name": get_category_display_name(category),
                "icon": get_category_icon(category),
                "configs": [self._serialize_config_brief(c) for c in all_configs],
                "has_default": default_config is not None,
                "default_provider": default_config.provider if default_config else None
            }
            result.append(category_data)

        return result

    # ============================================================
    # Default Configuration Management
    # ============================================================

    async def set_default(
        self,
        config_id: UUID,
        user_id: UUID
    ) -> UserApiConfig:
        """
        Set a configuration as the default for its category

        Args:
            config_id: Configuration ID
            user_id: User ID

        Returns:
            Updated configuration
        """
        config = self._get_user_config(config_id, user_id)

        if not config.is_active:
            raise ValidationError("Cannot set inactive configuration as default")

        # Unset other defaults
        self._unset_defaults(user_id, config.category)

        # Set this one as default
        config.is_default = True
        config.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(config)

        logger.info(f"Set API config {config_id} as default for {config.category}")

        return config

    # ============================================================
    # Configuration Retrieval for Integration Layer
    # ============================================================

    def get_user_or_system_config(
        self,
        user_id: Optional[UUID],
        category: str,
        provider: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a user, falling back to system config

        This is the main method used by the integration layer.

        Args:
            user_id: User ID (can be None for system-only)
            category: Configuration category
            provider: Specific provider (optional, uses default if not specified)

        Returns:
            Decrypted configuration dictionary or None
        """
        config = None

        # First, try to get user's configuration
        if user_id:
            query = self.db.query(UserApiConfig).filter(
                UserApiConfig.user_id == user_id,
                UserApiConfig.category == category,
                UserApiConfig.is_active == True
            )

            if provider:
                query = query.filter(UserApiConfig.provider == provider)
            else:
                # Get default or first active
                query = query.order_by(
                    UserApiConfig.is_default.desc(),
                    UserApiConfig.created_at.desc()
                )

            config = query.first()

        # Fall back to system configuration
        if not config:
            query = self.db.query(UserApiConfig).filter(
                UserApiConfig.is_system == True,
                UserApiConfig.category == category,
                UserApiConfig.is_active == True
            )

            if provider:
                query = query.filter(UserApiConfig.provider == provider)
            else:
                query = query.order_by(
                    UserApiConfig.is_default.desc(),
                    UserApiConfig.created_at.desc()
                )

            config = query.first()

        if not config:
            return None

        # Decrypt and return
        try:
            return decrypt_config(config.config_data)
        except Exception as e:
            logger.error(f"Failed to decrypt config {config.id}: {e}")
            return None

    def get_default_provider(
        self,
        user_id: Optional[UUID],
        category: str
    ) -> Optional[str]:
        """
        Get the default provider for a category

        Args:
            user_id: User ID
            category: Configuration category

        Returns:
            Provider name or None
        """
        config = None

        if user_id:
            config = self.db.query(UserApiConfig).filter(
                UserApiConfig.user_id == user_id,
                UserApiConfig.category == category,
                UserApiConfig.is_active == True,
                UserApiConfig.is_default == True
            ).first()

        if not config:
            config = self.db.query(UserApiConfig).filter(
                UserApiConfig.is_system == True,
                UserApiConfig.category == category,
                UserApiConfig.is_active == True,
                UserApiConfig.is_default == True
            ).first()

        return config.provider if config else None

    # ============================================================
    # Validation
    # ============================================================

    async def validate_config(
        self,
        category: str,
        provider: str,
        config_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate configuration data

        Args:
            category: Configuration category
            provider: Provider name
            config_data: Configuration data

        Returns:
            Tuple of (is_valid, error_message)
        """
        provider_def = get_provider_definition(provider, category)
        if not provider_def:
            return False, f"Unknown provider: {provider}"

        if provider_def.category.value != category:
            return False, f"Provider {provider} does not belong to category {category}"

        try:
            self._validate_config_data(provider_def.fields, config_data)
            return True, None
        except ValidationError as e:
            return False, str(e)

    async def mark_validated(
        self,
        config_id: UUID,
        user_id: UUID,
        is_valid: bool,
        error_message: Optional[str] = None
    ) -> None:
        """
        Mark a configuration as validated or invalid

        Args:
            config_id: Configuration ID
            user_id: User ID
            is_valid: Whether validation passed
            error_message: Error message if validation failed
        """
        config = self._get_user_config(config_id, user_id)
        config.is_validated = is_valid
        config.last_validated_at = datetime.utcnow()
        config.validation_error = error_message

        self.db.commit()

    # ============================================================
    # System Configuration Management
    # ============================================================

    async def create_system_config(
        self,
        category: str,
        provider: str,
        config_data: Dict[str, Any],
        display_name: Optional[str] = None,
        set_as_default: bool = True
    ) -> UserApiConfig:
        """
        Create a system-level configuration

        System configs are used as fallbacks when users don't have their own configs.

        Args:
            category: Configuration category
            provider: Provider name
            config_data: Configuration data
            display_name: Display name
            set_as_default: Set as default

        Returns:
            Created configuration
        """
        # Check if system config already exists
        existing = self.db.query(UserApiConfig).filter(
            UserApiConfig.user_id == None,
            UserApiConfig.category == category,
            UserApiConfig.provider == provider
        ).first()

        if existing:
            # Update existing
            existing.config_data = encrypt_config(config_data)
            if display_name:
                existing.display_name = display_name
            if set_as_default:
                self._unset_system_defaults(category)
                existing.is_default = True
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # Create new
        if set_as_default:
            self._unset_system_defaults(category)

        config = UserApiConfig(
            user_id=None,
            category=category,
            provider=provider,
            config_data=encrypt_config(config_data),
            display_name=display_name or provider,
            is_system=True,
            is_default=set_as_default,
        )

        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)

        logger.info(f"Created system API config: {category}/{provider}")

        return config

    # ============================================================
    # Private Helpers
    # ============================================================

    def _get_user_config(
        self,
        config_id: UUID,
        user_id: UUID,
        include_system: bool = False
    ) -> UserApiConfig:
        """Get a configuration, checking ownership"""
        query = self.db.query(UserApiConfig).filter(UserApiConfig.id == config_id)

        if include_system:
            query = query.filter(
                or_(
                    UserApiConfig.user_id == user_id,
                    UserApiConfig.is_system == True
                )
            )
        else:
            query = query.filter(UserApiConfig.user_id == user_id)

        config = query.first()

        if not config:
            raise NotFoundError("Configuration not found")

        return config

    def _validate_config_data(
        self,
        fields: List,
        config_data: Dict[str, Any]
    ) -> None:
        """Validate configuration data against field definitions"""
        for field in fields:
            value = config_data.get(field.name)

            if field.required and value is None:
                raise ValidationError(f"Field '{field.label}' is required")

            if value is not None:
                # Type validation
                if field.field_type == "number":
                    try:
                        num_value = float(value)
                        if field.min_value is not None and num_value < field.min_value:
                            raise ValidationError(
                                f"Field '{field.label}' must be at least {field.min_value}"
                            )
                        if field.max_value is not None and num_value > field.max_value:
                            raise ValidationError(
                                f"Field '{field.label}' must be at most {field.max_value}"
                            )
                    except (TypeError, ValueError):
                        raise ValidationError(f"Field '{field.label}' must be a number")

                # Note: We don't validate select field options strictly
                # because model names and other values change frequently
                # The options are just suggestions, users can input custom values

    def _unset_defaults(self, user_id: UUID, category: str) -> None:
        """Unset all defaults for a user in a category"""
        self.db.query(UserApiConfig).filter(
            UserApiConfig.user_id == user_id,
            UserApiConfig.category == category,
            UserApiConfig.is_default == True
        ).update({"is_default": False})

    def _unset_system_defaults(self, category: str) -> None:
        """Unset all system defaults in a category"""
        self.db.query(UserApiConfig).filter(
            UserApiConfig.user_id == None,
            UserApiConfig.category == category,
            UserApiConfig.is_system == True,
            UserApiConfig.is_default == True
        ).update({"is_default": False})

    def _serialize_config(
        self,
        config: UserApiConfig,
        include_decrypted: bool = False
    ) -> Dict[str, Any]:
        """Serialize a configuration for API response"""
        # Get sensitive field names for masking
        provider_def = get_provider_definition(config.provider, config.category)
        sensitive_fields = []
        if provider_def:
            sensitive_fields = [f.name for f in provider_def.fields if f.sensitive]

        # Decrypt and mask config data
        if include_decrypted:
            try:
                decrypted = decrypt_config(config.config_data)
                config_data = mask_config(decrypted, sensitive_fields)
            except Exception:
                config_data = {"_error": "Failed to decrypt"}
        else:
            config_data = {"_encrypted": True}

        return {
            "id": str(config.id),
            "user_id": str(config.user_id) if config.user_id else None,
            "category": config.category,
            "provider": config.provider,
            "display_name": config.display_name,
            "config_data": config_data,
            "is_active": config.is_active,
            "is_default": config.is_default,
            "is_system": config.is_system,
            "is_validated": config.is_validated,
            "last_validated_at": config.last_validated_at,
            "validation_error": config.validation_error,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }

    def _get_supported_providers(self, category: ApiCategory) -> List:
        """Return provider definitions that have a registered runtime client."""
        from app.integrations.client_factory import ClientFactory

        providers = get_providers_by_category(category)
        registered = set(ClientFactory.get_registered_providers(category.value))
        if not registered:
            return providers
        return [p for p in providers if p.provider in registered]

    def _serialize_config_brief(self, config: UserApiConfig) -> Dict[str, Any]:
        """Serialize a configuration briefly for listings"""
        return {
            "id": str(config.id),
            "category": config.category,
            "provider": config.provider,
            "display_name": config.display_name,
            "is_active": config.is_active,
            "is_default": config.is_default,
            "is_system": config.is_system,
            "is_validated": config.is_validated,
        }
