"""
认证相关的Pydantic模式
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any


class GitHubAuthResponse(BaseModel):
    """GitHub OAuth授权URL响应"""
    auth_url: str
    state: str


class GitHubCallbackRequest(BaseModel):
    """GitHub OAuth回调请求"""
    code: str


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class UserResponse(BaseModel):
    """用户信息响应"""
    id: str
    username: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    tier: str

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Token响应"""
    token: str
    expires_in: int
    user: UserResponse


class UserUpdateRequest(BaseModel):
    """用户信息更新请求"""
    username: Optional[str] = None
    avatar_url: Optional[str] = None


class UserUsageResponse(BaseModel):
    """用户用量统计响应"""
    user_id: str
    billing_cycle: dict
    videos_generated: int
    minutes: dict
    storage: dict
