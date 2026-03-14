"""
Pydantic schemas for API Configuration endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================
# Provider Schemas
# ============================================================

class ProviderFieldSchema(BaseModel):
    """Schema for a provider configuration field"""
    name: str
    label: str
    type: str  # text, password, number, select, url
    required: bool = True
    default: Optional[Any] = None
    placeholder: Optional[str] = ""
    description: Optional[str] = ""
    options: Optional[List[Dict[str, str]]] = None
    sensitive: bool = False
    min_value: Optional[float] = None
    max_value: Optional[float] = None


class ProviderSchema(BaseModel):
    """Schema for a provider definition"""
    provider: str
    display_name: str
    description: str
    category: str
    website_url: Optional[str] = ""
    icon: Optional[str] = ""
    fields: List[ProviderFieldSchema]


class CategorySchema(BaseModel):
    """Schema for a category with its providers"""
    category: str
    display_name: str
    icon: str
    providers: List[ProviderSchema]


class ProvidersResponse(BaseModel):
    """Response for all providers grouped by category"""
    categories: List[CategorySchema]


# ============================================================
# API Config Schemas
# ============================================================

class ApiConfigBase(BaseModel):
    """Base schema for API configuration"""
    category: str = Field(..., description="Configuration category")
    provider: str = Field(..., description="Provider name")
    display_name: Optional[str] = Field(None, description="User-friendly name")
    config_data: Dict[str, Any] = Field(..., description="Configuration data")


class ApiConfigCreateRequest(ApiConfigBase):
    """Request to create a new API configuration"""
    set_as_default: bool = Field(False, description="Set as default for this category")


class ApiConfigUpdateRequest(BaseModel):
    """Request to update an API configuration"""
    display_name: Optional[str] = None
    config_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ApiConfigResponse(BaseModel):
    """Response schema for API configuration"""
    id: str
    user_id: Optional[str] = None
    category: str
    provider: str
    display_name: Optional[str] = None
    config_data: Dict[str, Any]  # Masked for responses
    is_active: bool
    is_default: bool
    is_system: bool
    is_validated: bool
    last_validated_at: Optional[datetime] = None
    validation_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApiConfigListResponse(BaseModel):
    """Response for listing API configurations"""
    list: List[ApiConfigResponse]
    pagination: Dict[str, Any]


class ApiConfigValidateRequest(BaseModel):
    """Request to validate a configuration"""
    category: str
    provider: str
    config_data: Dict[str, Any]


class ApiConfigValidateResponse(BaseModel):
    """Response for configuration validation"""
    is_valid: bool
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ApiConfigSetDefaultResponse(BaseModel):
    """Response for setting default configuration"""
    id: str
    category: str
    provider: str
    is_default: bool
    message: str


# ============================================================
# Frontend Types
# ============================================================

class ApiConfigBrief(BaseModel):
    """Brief configuration info for listings"""
    id: str
    category: str
    provider: str
    display_name: Optional[str] = None
    is_active: bool
    is_default: bool
    is_system: bool
    is_validated: bool


class ApiConfigByCategory(BaseModel):
    """Configurations grouped by category"""
    category: str
    display_name: str
    icon: str
    configs: List[ApiConfigBrief]
    has_default: bool
    default_provider: Optional[str] = None
