"""
生成API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.generation import (
    AudioPreviewRequest,
    AudioPreviewResponse,
    AudioPreviewSaveRequest,
    ScriptGenerateRequest,
    ScriptGenerateResponse
)
from app.schemas.asset import AssetResponse
from app.services.generation_service import GenerationService
from app.models.user import User

router = APIRouter(prefix="/generation", tags=["Generation"])


@router.post("/audio-preview", response_model=AudioPreviewResponse)
async def generate_audio_preview(
    data: AudioPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    生成音频预览
    - 调用Index TTS API
    - 返回临时音频URL
    """
    service = GenerationService(db)
    try:
        return await service.generate_audio_preview(
            user_id=current_user.id,
            voice_id=data.voice_id,
            text=data.text,
            emotion=data.emotion,
            emotion_mode=data.emotion_mode,
            emotion_vector=data.emotion_vector,
            emotion_text=data.emotion_text,
            emotion_alpha=data.emotion_alpha,
            emotion_audio_asset_id=data.emotion_audio_asset_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/audio-preview/save", response_model=AssetResponse)
async def save_audio_preview(
    data: AudioPreviewSaveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    将音频预览保存到云存储并写入音色库。
    """
    service = GenerationService(db)
    try:
        return await service.save_audio_preview(
            user_id=current_user.id,
            audio_url=data.audio_url,
            title=data.title,
            voice_id=data.voice_id,
            text=data.text,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/script", response_model=ScriptGenerateResponse)
async def generate_script(
    data: ScriptGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI生成营销脚本
    - 调用GLM-4.7 API
    - 返回多个脚本选项
    """
    service = GenerationService(db)
    return await service.generate_script(
        user_id=current_user.id,
        product_name=data.product_name,
        product_description=data.product_description,
        target_audience=data.target_audience,
        tone=data.tone,
        duration_seconds=data.duration_seconds
    )
