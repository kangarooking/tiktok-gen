"""
用户API路由
"""
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.auth import UserResponse, UserUpdateRequest, UserUsageResponse
from app.services.user_service import UserService
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me/usage", response_model=UserUsageResponse)
async def get_user_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户用量统计
    - 视频生成数量
    - 分钟使用量
    - 存储使用量
    - 剩余额度
    """
    service = UserService(db)
    return await service.get_user_usage(current_user.id)


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新用户资料
    - 用户名
    - 头像URL
    """
    service = UserService(db)
    update_data = {}
    if data.username is not None:
        update_data["username"] = data.username
    if data.avatar_url is not None:
        update_data["avatar_url"] = data.avatar_url
    return await service.update_user(current_user.id, update_data)
