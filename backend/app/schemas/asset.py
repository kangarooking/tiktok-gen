"""
资产相关的Pydantic模式
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class AssetResponse(BaseModel):
    """资产响应"""
    id: str
    type: str
    title: str
    description: Optional[str] = None
    is_system: bool
    content: Optional[str] = None
    file_url: Optional[str] = None
    preview_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    status: str
    created_at: str
    tags: Optional[List[str]] = []

    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    """资产列表响应"""
    list: List[AssetResponse]
    pagination: dict


class AssetCreateRequest(BaseModel):
    """资产创建请求"""
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class AssetUpdateRequest(BaseModel):
    """资产更新请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class GenerateAvatarRequest(BaseModel):
    """AI生成形象请求"""
    title: str = Field(..., min_length=1, max_length=100)
    prompt: str = Field(..., min_length=1)
    reference_image_urls: Optional[List[str]] = Field(None, max_length=4)
