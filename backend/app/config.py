"""
配置管理 - 从环境变量加载配置
"""
from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    APP_NAME: str = "TikTokGen"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 3001

    # 数据库配置
    DATABASE_URL: str

    # Redis配置
    REDIS_URL: str
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # JWT配置
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7天

    # GitHub OAuth配置
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    GITHUB_REDIRECT_URI: str = "http://localhost:3000/auth/login/callback"

    # Index TTS配置
    INDEX_TTS_API_KEY: str = ""
    INDEX_TTS_BASE_URL: str = "https://api.302.ai"
    INDEX_TTS_TIMEOUT: int = 300

    # SiliconFlow TTS配置
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    SILICONFLOW_TTS_MODEL: str = "IndexTeam/IndexTTS-2"
    SILICONFLOW_TTS_VOICE: str = ""
    SILICONFLOW_TTS_TIMEOUT: int = 120

    # GLM-4.7 大模型配置
    GLM_API_KEY: str
    GLM_API_URL: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    GLM_MODEL: str = "glm-4.7"
    GLM_TIMEOUT: int = 60

    # Agnes AI 配置
    AGNES_API_KEY: str = ""
    AGNES_BASE_URL: str = "https://apihub.agnes-ai.com/v1"
    AGNES_LLM_MODEL: str = "agnes-2.0-flash"
    AGNES_IMAGE_MODEL: str = "agnes-image-2.1-flash"
    AGNES_VIDEO_MODEL: str = "agnes-video-v2.0"

    # APIMart GPT-Image-2 配置
    APIMART_API_KEY: str = ""
    APIMART_BASE_URL: str = "https://api.apimart.ai"

    # WaveSpeed AI数字人配置
    WAVESPEED_API_KEY: str
    WAVESPEED_API_BASE_URL: str = "https://api.302.ai/ws/api/v3"
    WAVESPEED_DEFAULT_RESOLUTION: str = "480p"
    WAVESPEED_TIMEOUT: int = 600

    # VolcEngine Ark Seedance 配置
    ARK_API_KEY: str = ""
    ARK_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    ARK_SEEDANCE_MODEL: str = "doubao-seedance-1-5-pro-251215"
    ARK_TIMEOUT: int = 600
    ARK_POLL_INTERVAL_SECONDS: int = 3
    ARK_SEEDANCE_DURATION: int = 5
    ARK_SEEDANCE_RESOLUTION: str = "720p"
    ARK_SEEDANCE_ASPECT_RATIO: str = "16:9"
    ARK_SEEDANCE_WATERMARK: bool = True
    ARK_SEEDANCE_CAMERA_FIXED: bool = False
    ARK_SEEDANCE_EXTRA_FLAGS: str = ""

    # 阿里云OSS配置
    OSS_ACCESS_KEY_ID: str
    OSS_ACCESS_KEY_SECRET: str
    OSS_BUCKET_NAME: str
    OSS_ENDPOINT: str
    OSS_REGION: str = "cn-beijing"
    OSS_PUBLIC_BASE_URL: str

    # ImgBB 图床配置
    IMGBB_API_KEY: str = ""
    IMGBB_BASE_URL: str = "https://api.imgbb.com/1/upload"
    IMGBB_EXPIRATION: int = 0

    # Banana Pro AI生图配置
    BANANA_PRO_API_KEY: str = ""
    BANANA_PRO_BASE_URL: str = "https://api.banana.pro/v1"
    BANANA_PRO_MODEL: str = "flux-pro"

    # 文件上传配置
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_IMAGE_FORMATS: str = "jpg,jpeg,png,webp"
    ALLOWED_AUDIO_FORMATS: str = "mp3,wav,m4a"
    ALLOWED_VIDEO_FORMATS: str = "mp4,mov,avi"

    # Celery配置
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    CELERY_TASK_TIMEOUT: int = 600
    CELERY_TASK_SOFT_TIMEOUT: int = 550

    # CORS配置
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS"
    CORS_ALLOW_HEADERS: str = "*"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001"  # 兼容

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text

    # 速率限制
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    @property
    def cors_origins_list(self) -> List[str]:
        """CORS origins列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def cors_methods_list(self) -> List[str]:
        """CORS methods列表"""
        return [method.strip() for method in self.CORS_ALLOW_METHODS.split(",")]

    @property
    def allowed_image_formats_list(self) -> List[str]:
        """允许的图片格式"""
        return [fmt.strip() for fmt in self.ALLOWED_IMAGE_FORMATS.split(",")]

    @property
    def allowed_audio_formats_list(self) -> List[str]:
        """允许的音频格式"""
        return [fmt.strip() for fmt in self.ALLOWED_AUDIO_FORMATS.split(",")]

    class Config:
        env_file = Path(__file__).resolve().parents[1] / ".env"
        case_sensitive = True


# 全局配置实例
settings = Settings()
