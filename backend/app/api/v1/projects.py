"""
项目API路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.project import (
    ProjectResponse,
    ProjectListResponse,
    ProjectCreateRequest,
    ProjectStatusResponse
)
from app.services.project_service import ProjectService
from app.models.user import User

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=ProjectListResponse)
async def get_projects(
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取项目列表
    - 按状态筛选
    - 按创建时间倒序
    """
    service = ProjectService(db)
    return await service.get_projects(
        user_id=current_user.id,
        status=status,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建视频生成项目
    - 验证资产权限
    - 验证用户额度
    - 创建项目记录
    - 触发异步生成任务
    """
    service = ProjectService(db)
    return await service.create_project(
        user_id=current_user.id,
        title=data.title,
        avatar_id=data.avatar_id,
        voice_id=data.voice_id,
        script_id=data.script_id,
        script_content=data.script_content,
        emotion=data.emotion,
        emotion_mode=data.emotion_mode,
        emotion_vector=data.emotion_vector,
        emotion_text=data.emotion_text,
        emotion_alpha=data.emotion_alpha,
        emotion_audio_asset_id=data.emotion_audio_asset_id,
        performance_prompt=data.performance_prompt,
        resolution=data.resolution,
        use_voice_audio_directly=data.use_voice_audio_directly
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取项目详情"""
    service = ProjectService(db)
    return await service.get_project(project_id, current_user.id)


@router.get("/{project_id}/status", response_model=ProjectStatusResponse)
async def get_project_status(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取项目生成状态
    - 用于前端轮询
    - 返回进度和当前步骤
    """
    service = ProjectService(db)
    return await service.get_project_status(project_id, current_user.id)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除项目"""
    service = ProjectService(db)
    await service.delete_project(project_id, current_user.id)
