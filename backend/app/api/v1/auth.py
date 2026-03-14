"""
认证API路由
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.auth import (
    GitHubAuthResponse,
    GitHubCallbackRequest,
    TokenResponse,
    UserResponse,
    RegisterRequest,
    LoginRequest
)
from app.services.auth_service import AuthService
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/github", response_model=GitHubAuthResponse)
async def get_github_auth_url(
    db: Session = Depends(get_db)
):
    """
    获取GitHub OAuth授权URL
    前端获取后跳转到GitHub进行授权
    """
    service = AuthService(db)
    return await service.get_github_auth_url()


@router.post("/github/callback", response_model=TokenResponse)
async def github_oauth_callback(
    data: GitHubCallbackRequest,
    db: Session = Depends(get_db)
):
    """
    GitHub OAuth回调处理
    - 用code换取access_token
    - 获取GitHub用户信息
    - 创建/更新本地用户记录
    - 生成JWT Token
    - 创建会话记录
    """
    service = AuthService(db)
    return await service.handle_github_callback(data.code)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户信息
    通过JWT Token识别用户
    """
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        avatar_url=current_user.avatar_url,
        tier=current_user.tier if isinstance(current_user.tier, str) else current_user.tier.value
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    登出
    - 将当前Token加入黑名单
    - 标记会话为失效
    """
    service = AuthService(db)
    await service.logout(current_user.id)


@router.post("/register", response_model=TokenResponse)
async def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    用户注册
    - 用户名密码注册
    - 自动创建会话
    """
    service = AuthService(db)
    return await service.register(data.username, data.password)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    用户登录
    - 用户名密码登录
    - 返回JWT Token
    """
    service = AuthService(db)
    return await service.login(data.username, data.password)
