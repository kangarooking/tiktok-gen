"""
生成相关的Pydantic模式
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class AudioPreviewRequest(BaseModel):
    """音频预览生成请求"""
    voice_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1, max_length=5000)
    emotion: Optional[str] = "professional"
    emotion_mode: Optional[str] = "preset"  # preset | vector | audio_ref | text_ref
    emotion_vector: Optional[List[float]] = None  # [高兴,愤怒,悲伤,害怕,厌恶,忧郁,惊讶,平静]
    emotion_text: Optional[str] = None
    emotion_alpha: Optional[float] = Field(default=None, ge=0, le=1)
    emotion_audio_asset_id: Optional[str] = None


class AudioPreviewResponse(BaseModel):
    """音频预览响应"""
    audio_url: str
    duration_seconds: float
    expires_in: int


class AudioPreviewSaveRequest(BaseModel):
    """保存音频预览请求"""
    audio_url: str = Field(..., min_length=1)
    title: Optional[str] = Field(default=None, max_length=100)
    voice_id: Optional[str] = None
    text: Optional[str] = Field(default=None, max_length=5000)


class ScriptGenerateRequest(BaseModel):
    """脚本生成请求"""
    product_name: str = Field(..., min_length=1, max_length=200)
    product_description: str = Field(..., min_length=1, max_length=2000)
    target_audience: Optional[str] = "普通消费者"
    tone: Optional[str] = "轻松活泼"
    duration_seconds: Optional[int] = 15


class ScriptInfo(BaseModel):
    """脚本信息"""
    content: str
    estimated_seconds: int
    word_count: int


class ScriptGenerateResponse(BaseModel):
    """脚本生成响应"""
    scripts: List[ScriptInfo]
