"""
项目相关的Pydantic模式
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ProjectAssetInfo(BaseModel):
    """项目关联资产信息"""
    id: str
    title: str
    file_url: Optional[str] = None
    content: Optional[str] = None


class ProjectResponse(BaseModel):
    """项目响应"""
    id: str
    title: str
    status: str
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    resolution: Optional[str] = None
    progress: Optional[int] = None
    current_step: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    assets: Dict[str, Optional[ProjectAssetInfo]]

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """项目列表响应"""
    list: List[ProjectResponse]
    pagination: dict


class ProjectCreateRequest(BaseModel):
    """项目创建请求"""
    title: Optional[str] = Field(None, max_length=200)
    avatar_id: str = Field(..., min_length=1)
    voice_id: str = Field(..., min_length=1)
    script_id: Optional[str] = None
    script_content: Optional[str] = None
    emotion: Optional[str] = "professional"
    emotion_mode: Optional[str] = "preset"
    emotion_vector: Optional[List[float]] = None
    emotion_text: Optional[str] = None
    emotion_alpha: Optional[float] = Field(default=None, ge=0, le=1)
    emotion_audio_asset_id: Optional[str] = None
    performance_prompt: Optional[str] = ""
    resolution: Optional[str] = "480p"
    use_voice_audio_directly: Optional[bool] = False
    video_generation_mode: Optional[str] = "tts_required"
    storyboard_asset_ids: Optional[List[str]] = None
    reference_image_asset_ids: Optional[List[str]] = None
    storyboard_mode: Optional[str] = "none"
    prompt_mode: Optional[str] = "script"
    prompt_only_video: Optional[bool] = False
    language: Optional[str] = "zh"


class ProjectStatusResponse(BaseModel):
    """项目状态响应"""
    id: str
    status: str
    progress: int
    current_step: str
    steps: List[Dict[str, str]]
    estimated_remaining_seconds: Optional[int] = None
    error: Optional[str] = None


class StepInfo(BaseModel):
    """步骤信息"""
    name: str
    status: str  # pending, processing, completed, failed
