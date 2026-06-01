"""
资产API路由
"""
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.asset import (
    AssetResponse,
    AssetListResponse,
    AssetCreateRequest,
    AssetUpdateRequest
)
from app.services.asset_service import AssetService
from app.models.user import User
from app.core.exceptions import APIException

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get("", response_model=AssetListResponse)
async def get_assets(
    type: str = Query(None, regex="^(avatar|voice|script|storyboard)$"),
    is_system: bool = Query(None),
    keyword: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取资产列表
    - 支持按类型筛选
    - 支持系统/用户筛选
    - 支持关键词搜索
    - 分页查询
    """
    service = AssetService(db)
    return await service.get_assets(
        user_id=current_user.id,
        asset_type=type,
        is_system=is_system,
        keyword=keyword,
        page=page,
        page_size=page_size
    )


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取资产详情
    - 用户可访问自己的资产和系统资产
    """
    service = AssetService(db)
    return await service.get_asset(asset_id, current_user.id)


@router.post("/scripts", response_model=AssetResponse)
async def create_script(
    title: str = Form(...),
    content: str = Form(...),
    tags: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建脚本资产
    - 验证脚本内容
    - 计算预估时长
    - 创建资产记录
    """
    service = AssetService(db)
    tag_list = tags.split(",") if tags else None
    return await service.create_script(current_user.id, title, content, tag_list)


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: str,
    data: AssetUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新资产信息
    - 仅允许更新自己的资产
    """
    service = AssetService(db)
    update_data = {}
    if data.title is not None:
        update_data["title"] = data.title
    if data.description is not None:
        update_data["description"] = data.description
    if data.metadata is not None:
        update_data["metadata"] = data.metadata
    return await service.update_asset(asset_id, current_user.id, update_data)


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除资产
    - 仅允许删除自己的资产
    - 不能删除已使用的资产
    """
    service = AssetService(db)
    await service.delete_asset(asset_id, current_user.id)


# 上传接口需要单独处理，因为使用FormData
@router.post("/avatars/upload", response_model=AssetResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    title: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传形象图片
    - 验证文件格式和大小
    - 上传到阿里云OSS
    - 创建资产记录
    """
    service = AssetService(db)
    return await service.upload_avatar(current_user.id, file, title)


@router.post("/avatars/generate", response_model=AssetResponse)
async def generate_avatar(
    title: str = Form(...),
    prompt: str = Form(...),
    style: str = Form(None),
    gender: str = Form(None),
    age_range: str = Form(None),
    reference_images: list[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI生成头像
    - 使用Banana Pro API生成头像
    - 支持以图生图（上传参考图片）
    - 下载并上传到阿里云OSS
    - 创建资产记录
    """
    service = AssetService(db)
    try:
        return await service.generate_avatar(
            current_user.id, title, prompt, style, gender, age_range, reference_images
        )
    except APIException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI image generation failed: {exc}")


@router.post("/voices/upload", response_model=AssetResponse)
async def upload_voice(
    file: UploadFile = File(...),
    title: str = Form(...),
    gender: str = Form(None),
    tags: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传音色音频
    - 验证文件格式和大小
    - 上传到阿里云OSS
    - 创建资产记录
    """
    service = AssetService(db)
    tag_list = tags.split(",") if tags else None
    return await service.upload_voice(current_user.id, file, title, gender, tag_list)
