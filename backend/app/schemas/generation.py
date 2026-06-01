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


class StoryboardGenerateRequest(BaseModel):
    """图片分镜生成请求"""
    script_content: str = Field(..., min_length=1, max_length=8000)
    product_name: Optional[str] = Field(default=None, max_length=200)
    user_prompt: Optional[str] = Field(default=None, max_length=3000)
    style: Optional[str] = Field(default="电影感 TikTok 商品广告，真实商业摄影风格", max_length=1200)
    frame_count: int = Field(default=3, ge=1, le=6)
    aspect_ratio: Optional[str] = "9:16"
    image_provider: Optional[str] = None
    reference_image_url: Optional[str] = Field(default=None, max_length=2000)
    language: Optional[str] = "zh"


class StoryboardFrameInfo(BaseModel):
    """单张分镜信息"""
    asset_id: str
    scene_index: int
    prompt: str
    video_prompt: Optional[str] = None
    image_url: str


class StoryboardGenerateResponse(BaseModel):
    """图片分镜生成响应"""
    storyboard_id: str
    frames: List[StoryboardFrameInfo]
