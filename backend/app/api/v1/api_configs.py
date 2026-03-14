"""
API Configuration Endpoints

REST API for managing user API configurations for third-party services.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.api_config import (
    ApiConfigCreateRequest,
    ApiConfigUpdateRequest,
    ApiConfigResponse,
    ApiConfigListResponse,
    ApiConfigValidateRequest,
    ApiConfigValidateResponse,
    ApiConfigSetDefaultResponse,
    ProvidersResponse,
)
from app.services.api_config_service import ApiConfigService
from app.integrations.client_factory import ClientFactory
from app.integrations.siliconflow_tts import SiliconFlowTTSClient
from app.config import settings

router = APIRouter(prefix="/api-configs", tags=["API Configurations"])


@router.get("/providers", response_model=ProvidersResponse)
async def get_all_providers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all available providers grouped by category

    Returns provider definitions with field schemas for configuration forms.
    """
    service = ApiConfigService(db)
    return service.get_all_providers()


@router.get("/providers/tts/siliconflow/models")
async def get_siliconflow_audio_models(
    api_key: Optional[str] = Query(None, description="SiliconFlow API key (optional)"),
    base_url: Optional[str] = Query(None, description="SiliconFlow base URL (optional)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get latest SiliconFlow audio model list.

    API key priority:
    1) query param api_key
    2) current user's siliconflow_tts config
    3) system siliconflow_tts config
    4) SILICONFLOW_API_KEY env
    """
    service = ApiConfigService(db)

    selected_api_key = (api_key or "").strip()
    selected_base_url = (base_url or "").strip()

    if not selected_api_key:
        cfg = service.get_user_or_system_config(
            user_id=current_user.id,
            category="tts",
            provider="siliconflow_tts"
        )
        if cfg:
            selected_api_key = (cfg.get("api_key") or "").strip()
            if not selected_base_url:
                selected_base_url = (cfg.get("base_url") or "").strip()

    if not selected_api_key:
        selected_api_key = (settings.SILICONFLOW_API_KEY or "").strip()

    if not selected_base_url:
        selected_base_url = (settings.SILICONFLOW_BASE_URL or "https://api.siliconflow.cn/v1").strip()

    if not selected_api_key:
        raise HTTPException(status_code=400, detail="SiliconFlow API key is required")

    try:
        models = await SiliconFlowTTSClient.list_audio_models(
            api_key=selected_api_key,
            base_url=selected_base_url,
        )
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch SiliconFlow models: {e}")


@router.get("/providers/{category}")
async def get_providers_by_category(
    category: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all providers for a specific category

    Args:
        category: One of ai_image, cloud_storage, digital_human, tts, llm
    """
    service = ApiConfigService(db)
    return service.get_providers_for_category(category)


@router.get("", response_model=ApiConfigListResponse)
async def list_configs(
    category: Optional[str] = Query(None, description="Filter by category"),
    include_system: bool = Query(True, description="Include system-level configs"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all API configurations for the current user

    Returns both user configurations and system-level fallbacks.
    """
    service = ApiConfigService(db)
    return await service.list_configs(
        user_id=current_user.id,
        category=category,
        include_system=include_system,
        page=page,
        page_size=page_size
    )


@router.get("/by-category")
async def get_configs_by_category(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get configurations grouped by category

    Returns a summary of configurations for each category,
    useful for settings page overview.
    """
    service = ApiConfigService(db)
    return await service.get_configs_by_category(current_user.id)


@router.get("/{config_id}", response_model=ApiConfigResponse)
async def get_config(
    config_id: str,
    include_decrypted: bool = Query(False, description="Include decrypted (masked) config data"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific configuration by ID

    Returns decrypted and masked configuration data.
    """
    from uuid import UUID

    try:
        config_uuid = UUID(config_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid configuration ID")

    service = ApiConfigService(db)
    return await service.get_config(
        config_id=config_uuid,
        user_id=current_user.id,
        include_decrypted=include_decrypted
    )


@router.post("", response_model=ApiConfigResponse)
async def create_config(
    data: ApiConfigCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API configuration

    Validates the configuration against the provider's schema and encrypts
    sensitive data before storage.
    """
    service = ApiConfigService(db)
    config = await service.create_config(
        user_id=current_user.id,
        category=data.category,
        provider=data.provider,
        config_data=data.config_data,
        display_name=data.display_name,
        set_as_default=data.set_as_default
    )

    return await service.get_config(
        config_id=config.id,
        user_id=current_user.id,
        include_decrypted=True
    )


@router.put("/{config_id}", response_model=ApiConfigResponse)
async def update_config(
    config_id: str,
    data: ApiConfigUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing configuration

    Only provided fields will be updated. Configuration data will be re-encrypted.
    """
    from uuid import UUID

    try:
        config_uuid = UUID(config_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid configuration ID")

    service = ApiConfigService(db)
    config = await service.update_config(
        config_id=config_uuid,
        user_id=current_user.id,
        display_name=data.display_name,
        config_data=data.config_data,
        is_active=data.is_active
    )

    return await service.get_config(
        config_id=config.id,
        user_id=current_user.id,
        include_decrypted=True
    )


@router.delete("/{config_id}", status_code=204)
async def delete_config(
    config_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a configuration

    Cannot delete system-level configurations.
    """
    from uuid import UUID

    try:
        config_uuid = UUID(config_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid configuration ID")

    service = ApiConfigService(db)
    await service.delete_config(config_id=config_uuid, user_id=current_user.id)


@router.post("/validate", response_model=ApiConfigValidateResponse)
async def validate_config(
    data: ApiConfigValidateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate configuration data

    Checks if the configuration has all required fields and valid values.
    Does not store the configuration.
    """
    service = ApiConfigService(db)
    is_valid, error_message = await service.validate_config(
        category=data.category,
        provider=data.provider,
        config_data=data.config_data
    )

    return ApiConfigValidateResponse(
        is_valid=is_valid,
        message=error_message or "Configuration is valid"
    )


@router.post("/{config_id}/set-default", response_model=ApiConfigSetDefaultResponse)
async def set_default_config(
    config_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Set a configuration as the default for its category

    Only one configuration per category can be default.
    """
    from uuid import UUID

    try:
        config_uuid = UUID(config_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid configuration ID")

    service = ApiConfigService(db)
    config = await service.set_default(
        config_id=config_uuid,
        user_id=current_user.id
    )

    return ApiConfigSetDefaultResponse(
        id=str(config.id),
        category=config.category,
        provider=config.provider,
        is_default=config.is_default,
        message=f"{config.display_name} is now the default for {config.category}"
    )


@router.post("/{config_id}/validate-connection", response_model=ApiConfigValidateResponse)
async def validate_connection(
    config_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate the connection using this configuration

    Attempts to make a test API call to verify the configuration works.
    """
    from uuid import UUID

    try:
        config_uuid = UUID(config_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid configuration ID")

    service = ApiConfigService(db)

    # Get raw config and run integration-level validation.
    config_record, raw_config = await service.get_decrypted_config_for_runtime(
        config_id=config_uuid,
        user_id=current_user.id
    )

    try:
        client = ClientFactory.create_client_from_config(
            category=config_record.category,
            provider=config_record.provider,
            config=raw_config
        )
        is_valid, error_message = await client.validate_config()
    except Exception as e:
        is_valid = False
        error_message = str(e)

    await service.mark_validated(
        config_id=config_uuid,
        user_id=current_user.id,
        is_valid=is_valid,
        error_message=error_message
    )

    return ApiConfigValidateResponse(
        is_valid=is_valid,
        message=error_message or "Connection validated successfully",
        details={"provider": config_record.provider}
    )
