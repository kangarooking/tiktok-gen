"""
常量定义
"""
from enum import Enum


# 用户订阅等级
class UserTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# 资产类型
class AssetType(str, Enum):
    AVATAR = "avatar"
    VOICE = "voice"
    SCRIPT = "script"
    STORYBOARD = "storyboard"


# 资产来源
class AssetSource(str, Enum):
    SYSTEM = "system"
    UPLOAD = "upload"
    AI_GENERATED = "ai_generated"


# 资产状态
class AssetStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


# 项目状态
class ProjectStatus(str, Enum):
    PENDING = "pending"
    GENERATING_AUDIO = "generating_audio"
    GENERATING_VIDEO = "generating_video"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"
    FAILED = "failed"


# OAuth提供商
class OAuthProvider(str, Enum):
    GITHUB = "github"
    GOOGLE = "google"
    WECHAT = "wechat"


# 情绪风格
class EmotionStyle(str, Enum):
    HAPPY = "happy"
    PROFESSIONAL = "professional"
    GENTLE = "gentle"
    EXCITED = "excited"
    SERIOUS = "serious"


# 视频分辨率
class VideoResolution(str, Enum):
    P480 = "480p"
    P720 = "720p"
    P1080 = "1080p"


# 日志级别
class LogLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"


# 订阅计划配置
SUBSCRIPTION_PLANS = {
    UserTier.FREE: {
        "name": "免费版",
        "description": "适合个人尝鲜使用",
        "minutes_per_month": 10,
        "storage_mb": 100,
        "max_resolution": VideoResolution.P480,
        "max_assets": 50,
        "features": {
            "ai_avatar_generation": False,
            "voice_cloning": False,
            "priority_queue": False,
            "api_access": False
        }
    },
    UserTier.PRO: {
        "name": "专业版",
        "description": "适合个人创作者和小团队",
        "minutes_per_month": 60,
        "storage_mb": 1024,
        "max_resolution": VideoResolution.P720,
        "max_assets": 500,
        "features": {
            "ai_avatar_generation": True,
            "voice_cloning": True,
            "priority_queue": False,
            "api_access": False
        }
    },
    UserTier.ENTERPRISE: {
        "name": "企业版",
        "description": "适合企业和MCN机构",
        "minutes_per_month": 300,
        "storage_mb": 10240,
        "max_resolution": VideoResolution.P1080,
        "max_assets": -1,  # 无限制
        "features": {
            "ai_avatar_generation": True,
            "voice_cloning": True,
            "priority_queue": True,
            "api_access": True
        }
    }
}

# 情绪选项
EMOTION_OPTIONS = [
    {"id": EmotionStyle.HAPPY, "label": "快乐", "icon": "smile"},
    {"id": EmotionStyle.PROFESSIONAL, "label": "专业", "icon": "briefcase"},
    {"id": EmotionStyle.GENTLE, "label": "温柔", "icon": "heart"},
    {"id": EmotionStyle.EXCITED, "label": "兴奋", "icon": "zap"},
    {"id": EmotionStyle.SERIOUS, "label": "严肃", "icon": "graduation-cap"},
]
