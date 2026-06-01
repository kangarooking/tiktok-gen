"""
Provider Constants - API Categories and Provider Definitions

This module defines all supported API categories, providers, and their configuration schemas.
"""
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


class ApiCategory(str, Enum):
    """API service categories"""
    AI_IMAGE = "ai_image"
    CLOUD_STORAGE = "cloud_storage"
    DIGITAL_HUMAN = "digital_human"
    TTS = "tts"
    LLM = "llm"


class AIImageProvider(str, Enum):
    """AI Image generation providers"""
    BANANA_PRO = "banana_pro"
    NANOBANANA_PRO = "nanobanana_pro"
    AGNES_IMAGE = "agnes_image"
    APIMART_GPT_IMAGE2 = "apimart_gpt_image2"
    CUSTOM_OPENAI = "custom_openai"


class CloudStorageProvider(str, Enum):
    """Cloud storage providers"""
    ALIYUN_OSS = "aliyun_oss"
    IMGBB = "imgbb"
    TENCENT_COS = "tencent_cos"
    QINIU = "qiniu"


class DigitalHumanProvider(str, Enum):
    """Digital human video generation providers"""
    WAVESPEED = "wavespeed"
    ARK_SEEDANCE = "ark_seedance"
    AGNES_VIDEO = "agnes_video"
    JIMENG = "jimeng"
    SORA = "sora"
    VEO = "veo"
    KELING = "keling"
    HAILUO = "hailuo"
    CUSTOM = "custom"


class TTSProvider(str, Enum):
    """Text-to-speech providers"""
    INDEX_TTS = "index_tts"
    SILICONFLOW_TTS = "siliconflow_tts"
    MINIMAX = "minimax"
    OPENAI_TTS = "openai_tts"
    CUSTOM = "custom"


class LLMProvider(str, Enum):
    """Large language model providers"""
    GLM = "glm"
    AGNES = "agnes"
    OPENAI = "openai"
    GEMINI = "gemini"
    BAIDU_WENXIN = "baidu_wenxin"
    KIMI = "kimi"
    CUSTOM = "custom"


@dataclass
class ProviderField:
    """Configuration field definition"""
    name: str
    label: str
    field_type: str  # 'text', 'password', 'number', 'select', 'url'
    required: bool = True
    default: Any = None
    placeholder: str = ""
    description: str = ""
    options: List[Dict[str, str]] = field(default_factory=list)  # For select fields
    sensitive: bool = False  # Whether to mask in API responses
    min_value: Optional[float] = None
    max_value: Optional[float] = None


@dataclass
class ProviderDefinition:
    """Complete provider definition"""
    provider: str
    display_name: str
    description: str
    category: ApiCategory
    fields: List[ProviderField]
    website_url: str = ""
    icon: str = ""


# ============================================================
# Provider Definitions
# ============================================================

PROVIDER_DEFINITIONS: Dict[str, ProviderDefinition] = {
    # ==================== AI Image Providers ====================
    "banana_pro": ProviderDefinition(
        provider="banana_pro",
        display_name="Banana Pro",
        description="AI image generation service",
        category=ApiCategory.AI_IMAGE,
        website_url="https://www.banana.pro",
        icon="image",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your Banana Pro API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                default="https://api.banana.pro/v1",
                placeholder="https://api.banana.pro/v1"
            ),
            ProviderField(
                name="model",
                label="Model",
                field_type="text",
                required=True,
                default="flux-pro",
                placeholder="flux-pro"
            ),
        ]
    ),

    "nanobanana_pro": ProviderDefinition(
        provider="nanobanana_pro",
        display_name="NanoBanana Pro",
        description="Official NanoBanana Pro image generation",
        category=ApiCategory.AI_IMAGE,
        website_url="https://nanobanana.pro",
        icon="image",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your NanoBanana API key",
                sensitive=True
            ),
        ]
    ),

    "custom_openai": ProviderDefinition(
        provider="custom_openai",
        display_name="Custom OpenAI Compatible",
        description="Any OpenAI-compatible image generation API",
        category=ApiCategory.AI_IMAGE,
        icon="image",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                placeholder="https://api.example.com/v1"
            ),
            ProviderField(
                name="model",
                label="Model Name",
                field_type="text",
                required=True,
                placeholder="dall-e-3"
            ),
        ]
    ),

    "agnes_image": ProviderDefinition(
        provider="agnes_image",
        display_name="Agnes Image 2.1 Flash",
        description="Agnes text-to-image and image-to-image generation",
        category=ApiCategory.AI_IMAGE,
        website_url="https://agnes-ai.com",
        icon="image",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your Agnes API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                default="https://apihub.agnes-ai.com/v1",
                placeholder="https://apihub.agnes-ai.com/v1"
            ),
            ProviderField(
                name="model",
                label="Model",
                field_type="text",
                required=True,
                default="agnes-image-2.1-flash",
                placeholder="agnes-image-2.1-flash"
            ),
            ProviderField(
                name="size",
                label="Default Size",
                field_type="text",
                required=False,
                default="1024x768",
                placeholder="1024x768"
            ),
            ProviderField(
                name="timeout",
                label="Timeout (seconds)",
                field_type="number",
                required=False,
                default=180,
                min_value=30,
                max_value=600
            ),
        ]
    ),

    "apimart_gpt_image2": ProviderDefinition(
        provider="apimart_gpt_image2",
        display_name="APIMart GPT-Image-2",
        description="APIMart hosted GPT-Image-2 async image generation",
        category=ApiCategory.AI_IMAGE,
        website_url="https://docs.apimart.ai",
        icon="image",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your APIMart API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                default="https://api.apimart.ai",
                placeholder="https://api.apimart.ai"
            ),
            ProviderField(
                name="model",
                label="Model",
                field_type="text",
                required=True,
                default="gpt-image-2",
                placeholder="gpt-image-2"
            ),
            ProviderField(
                name="size",
                label="Default Size",
                field_type="select",
                required=False,
                default="9:16",
                options=[
                    {"value": "9:16", "label": "9:16"},
                    {"value": "16:9", "label": "16:9"},
                    {"value": "1:1", "label": "1:1"},
                    {"value": "4:5", "label": "4:5"},
                    {"value": "5:4", "label": "5:4"},
                    {"value": "auto", "label": "auto"},
                ]
            ),
            ProviderField(
                name="resolution",
                label="Resolution",
                field_type="select",
                required=False,
                default="1k",
                options=[
                    {"value": "1k", "label": "1k"},
                    {"value": "2k", "label": "2k"},
                    {"value": "4k", "label": "4k"},
                ]
            ),
            ProviderField(
                name="official_fallback",
                label="Official Fallback",
                field_type="select",
                required=False,
                default="false",
                options=[
                    {"value": "false", "label": "false"},
                    {"value": "true", "label": "true"},
                ]
            ),
            ProviderField(
                name="poll_interval",
                label="Poll Interval (seconds)",
                field_type="number",
                required=False,
                default=5,
                min_value=1,
                max_value=30
            ),
            ProviderField(
                name="timeout",
                label="Timeout (seconds)",
                field_type="number",
                required=False,
                default=300,
                min_value=30,
                max_value=1800
            ),
        ]
    ),

    # ==================== Cloud Storage Providers ====================
    "aliyun_oss": ProviderDefinition(
        provider="aliyun_oss",
        display_name="Aliyun OSS",
        description="Aliyun Object Storage Service",
        category=ApiCategory.CLOUD_STORAGE,
        website_url="https://www.aliyun.com/product/oss",
        icon="cloud",
        fields=[
            ProviderField(
                name="access_key_id",
                label="Access Key ID",
                field_type="text",
                required=True,
                placeholder="Enter your Access Key ID",
                sensitive=True
            ),
            ProviderField(
                name="access_key_secret",
                label="Access Key Secret",
                field_type="password",
                required=True,
                placeholder="Enter your Access Key Secret",
                sensitive=True
            ),
            ProviderField(
                name="bucket_name",
                label="Bucket Name",
                field_type="text",
                required=True,
                placeholder="my-bucket"
            ),
            ProviderField(
                name="endpoint",
                label="Endpoint",
                field_type="url",
                required=True,
                placeholder="oss-cn-beijing.aliyuncs.com"
            ),
            ProviderField(
                name="region",
                label="Region",
                field_type="text",
                required=False,
                default="cn-beijing",
                placeholder="cn-beijing"
            ),
            ProviderField(
                name="public_base_url",
                label="Public Base URL",
                field_type="url",
                required=True,
                placeholder="https://my-bucket.oss-cn-beijing.aliyuncs.com"
            ),
        ]
    ),

    "imgbb": ProviderDefinition(
        provider="imgbb",
        display_name="ImgBB",
        description="ImgBB image hosting for public image URLs",
        category=ApiCategory.CLOUD_STORAGE,
        website_url="https://api.imgbb.com/",
        icon="image",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your ImgBB API key",
                sensitive=True,
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                default="https://api.imgbb.com/1/upload",
                placeholder="https://api.imgbb.com/1/upload",
            ),
            ProviderField(
                name="expiration",
                label="Expiration (seconds)",
                field_type="number",
                required=False,
                default=0,
                min_value=0,
                max_value=15552000,
                description="0 means permanent image link",
            ),
            ProviderField(
                name="timeout",
                label="Timeout (seconds)",
                field_type="number",
                required=False,
                default=60,
                min_value=10,
                max_value=300,
            ),
        ],
    ),

    "tencent_cos": ProviderDefinition(
        provider="tencent_cos",
        display_name="Tencent COS",
        description="Tencent Cloud Object Storage",
        category=ApiCategory.CLOUD_STORAGE,
        website_url="https://cloud.tencent.com/product/cos",
        icon="cloud",
        fields=[
            ProviderField(
                name="secret_id",
                label="Secret ID",
                field_type="text",
                required=True,
                placeholder="Enter your Secret ID",
                sensitive=True
            ),
            ProviderField(
                name="secret_key",
                label="Secret Key",
                field_type="password",
                required=True,
                placeholder="Enter your Secret Key",
                sensitive=True
            ),
            ProviderField(
                name="bucket",
                label="Bucket",
                field_type="text",
                required=True,
                placeholder="my-bucket-1250000000"
            ),
            ProviderField(
                name="region",
                label="Region",
                field_type="text",
                required=True,
                placeholder="ap-beijing"
            ),
        ]
    ),

    "qiniu": ProviderDefinition(
        provider="qiniu",
        display_name="Qiniu Cloud",
        description="Qiniu Cloud Storage",
        category=ApiCategory.CLOUD_STORAGE,
        website_url="https://www.qiniu.com",
        icon="cloud",
        fields=[
            ProviderField(
                name="access_key",
                label="Access Key",
                field_type="text",
                required=True,
                placeholder="Enter your Access Key",
                sensitive=True
            ),
            ProviderField(
                name="secret_key",
                label="Secret Key",
                field_type="password",
                required=True,
                placeholder="Enter your Secret Key",
                sensitive=True
            ),
            ProviderField(
                name="bucket",
                label="Bucket",
                field_type="text",
                required=True,
                placeholder="my-bucket"
            ),
            ProviderField(
                name="domain",
                label="Domain",
                field_type="url",
                required=True,
                placeholder="https://cdn.example.com"
            ),
        ]
    ),

    # ==================== Digital Human Providers ====================
    "wavespeed": ProviderDefinition(
        provider="wavespeed",
        display_name="WaveSpeed AI (302.ai)",
        description="Digital human video generation via 302.ai",
        category=ApiCategory.DIGITAL_HUMAN,
        website_url="https://302.ai",
        icon="video",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your 302.ai API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                default="https://api.302.ai/ws/api/v3",
                placeholder="https://api.302.ai/ws/api/v3"
            ),
        ]
    ),

    "ark_seedance": ProviderDefinition(
        provider="ark_seedance",
        display_name="VolcEngine Seedance 1.5",
        description="VolcEngine Ark Seedance video generation (image + prompt)",
        category=ApiCategory.DIGITAL_HUMAN,
        website_url="https://www.volcengine.com",
        icon="video",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your ARK API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                default="https://ark.cn-beijing.volces.com/api/v3",
                placeholder="https://ark.cn-beijing.volces.com/api/v3"
            ),
            ProviderField(
                name="model",
                label="Model",
                field_type="text",
                required=True,
                default="doubao-seedance-1-5-pro-251215",
                placeholder="doubao-seedance-1-5-pro-251215"
            ),
            ProviderField(
                name="poll_interval",
                label="Poll Interval (seconds)",
                field_type="number",
                required=False,
                default=3,
                min_value=1,
                max_value=10
            ),
            ProviderField(
                name="duration",
                label="Duration (seconds)",
                field_type="select",
                required=False,
                default="5",
                options=[
                    {"value": "5", "label": "5s"},
                    {"value": "10", "label": "10s"},
                ]
            ),
            ProviderField(
                name="resolution",
                label="Resolution",
                field_type="select",
                required=False,
                default="720p",
                options=[
                    {"value": "480p", "label": "480p"},
                    {"value": "720p", "label": "720p"},
                    {"value": "1080p", "label": "1080p"},
                ]
            ),
            ProviderField(
                name="aspect_ratio",
                label="Aspect Ratio",
                field_type="select",
                required=False,
                default="16:9",
                options=[
                    {"value": "16:9", "label": "16:9"},
                    {"value": "9:16", "label": "9:16"},
                    {"value": "1:1", "label": "1:1"},
                    {"value": "4:3", "label": "4:3"},
                    {"value": "3:4", "label": "3:4"},
                ]
            ),
            ProviderField(
                name="camera_fixed",
                label="Camera Fixed",
                field_type="select",
                required=False,
                default="false",
                options=[
                    {"value": "false", "label": "false"},
                    {"value": "true", "label": "true"},
                ]
            ),
            ProviderField(
                name="watermark",
                label="Watermark",
                field_type="select",
                required=False,
                default="true",
                options=[
                    {"value": "true", "label": "true"},
                    {"value": "false", "label": "false"},
                ]
            ),
            ProviderField(
                name="extra_flags",
                label="Extra Flags",
                field_type="text",
                required=False,
                placeholder="e.g. --style cinematic --motion fast",
                description="Appended to prompt tail for advanced Seedance parameters"
            ),
            ProviderField(
                name="timeout",
                label="Timeout (seconds)",
                field_type="number",
                required=False,
                default=600,
                min_value=30,
                max_value=1800
            ),
        ]
    ),

    "agnes_video": ProviderDefinition(
        provider="agnes_video",
        display_name="Agnes Video V2.0",
        description="Agnes audio-synced text/image/keyframe video generation",
        category=ApiCategory.DIGITAL_HUMAN,
        website_url="https://agnes-ai.com",
        icon="video",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your Agnes API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                default="https://apihub.agnes-ai.com/v1",
                placeholder="https://apihub.agnes-ai.com/v1"
            ),
            ProviderField(
                name="model",
                label="Model",
                field_type="text",
                required=True,
                default="agnes-video-v2.0",
                placeholder="agnes-video-v2.0"
            ),
            ProviderField(
                name="width",
                label="Width",
                field_type="number",
                required=False,
                default=1152,
                min_value=256,
                max_value=2048
            ),
            ProviderField(
                name="height",
                label="Height",
                field_type="number",
                required=False,
                default=768,
                min_value=256,
                max_value=2048
            ),
            ProviderField(
                name="num_frames",
                label="Frame Count",
                field_type="number",
                required=False,
                default=193,
                description="Must be <= 441 and satisfy 8n + 1",
                min_value=9,
                max_value=441
            ),
            ProviderField(
                name="frame_rate",
                label="FPS",
                field_type="number",
                required=False,
                default=24,
                min_value=1,
                max_value=60
            ),
            ProviderField(
                name="negative_prompt",
                label="Negative Prompt",
                field_type="text",
                required=False,
                placeholder="blur, low quality, distorted face"
            ),
            ProviderField(
                name="poll_interval",
                label="Poll Interval (seconds)",
                field_type="number",
                required=False,
                default=5,
                min_value=1,
                max_value=30
            ),
            ProviderField(
                name="timeout",
                label="Timeout (seconds)",
                field_type="number",
                required=False,
                default=1800,
                min_value=60,
                max_value=1800
            ),
        ]
    ),

    "jimeng": ProviderDefinition(
        provider="jimeng",
        display_name="Jimeng AI",
        description="Jimeng AI video generation",
        category=ApiCategory.DIGITAL_HUMAN,
        website_url="https://jimeng.jianying.com",
        icon="video",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                placeholder="https://api.jimeng.ai"
            ),
        ]
    ),

    "sora": ProviderDefinition(
        provider="sora",
        display_name="Sora",
        description="OpenAI Sora video generation",
        category=ApiCategory.DIGITAL_HUMAN,
        website_url="https://openai.com/sora",
        icon="video",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your OpenAI API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                default="https://api.openai.com/v1",
                placeholder="https://api.openai.com/v1"
            ),
        ]
    ),

    "veo": ProviderDefinition(
        provider="veo",
        display_name="Veo 3.1",
        description="Google Veo video generation",
        category=ApiCategory.DIGITAL_HUMAN,
        website_url="https://deepmind.google/technologies/veo",
        icon="video",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your Google API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                placeholder="https://generativelanguage.googleapis.com/v1"
            ),
        ]
    ),

    "keling": ProviderDefinition(
        provider="keling",
        display_name="Keling AI",
        description="Keling AI video generation",
        category=ApiCategory.DIGITAL_HUMAN,
        website_url="https://klingai.kuaishou.com",
        icon="video",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                placeholder="https://api.kelingai.kuaishou.com"
            ),
        ]
    ),

    "hailuo": ProviderDefinition(
        provider="hailuo",
        display_name="Hailuo AI",
        description="Hailuo AI video generation",
        category=ApiCategory.DIGITAL_HUMAN,
        website_url="https://www.hailuo.ai",
        icon="video",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                placeholder="https://api.hailuo.ai"
            ),
        ]
    ),

    "digital_human_custom": ProviderDefinition(
        provider="custom",
        display_name="Custom API",
        description="Custom digital human API",
        category=ApiCategory.DIGITAL_HUMAN,
        icon="video",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                placeholder="https://api.example.com"
            ),
            ProviderField(
                name="model",
                label="Model",
                field_type="text",
                required=False,
                placeholder="Model name (optional)"
            ),
        ]
    ),

    # ==================== TTS Providers ====================
    "index_tts": ProviderDefinition(
        provider="index_tts",
        display_name="Index TTS (302.AI)",
        description="302.AI hosted Index TTS v2 task API",
        category=ApiCategory.TTS,
        website_url="https://api.302.ai",
        icon="mic",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your 302 API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                default="https://api.302.ai",
                placeholder="https://api.302.ai"
            ),
            ProviderField(
                name="timeout",
                label="Timeout (seconds)",
                field_type="number",
                required=False,
                default=300,
                min_value=10,
                max_value=600
            ),
        ]
    ),

    "siliconflow_tts": ProviderDefinition(
        provider="siliconflow_tts",
        display_name="SiliconFlow TTS",
        description="SiliconFlow speech synthesis API (/audio/speech)",
        category=ApiCategory.TTS,
        website_url="https://siliconflow.cn",
        icon="mic",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your SiliconFlow API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                default="https://api.siliconflow.cn/v1",
                placeholder="https://api.siliconflow.cn/v1"
            ),
            ProviderField(
                name="model",
                label="Model",
                field_type="select",
                required=True,
                default="IndexTeam/IndexTTS-2",
                options=[
                    {"value": "IndexTeam/IndexTTS-2", "label": "IndexTeam/IndexTTS-2"},
                    {"value": "FunAudioLLM/CosyVoice2-0.5B", "label": "FunAudioLLM/CosyVoice2-0.5B"},
                    {"value": "fnlp/MOSS-TTSD-v0.5", "label": "fnlp/MOSS-TTSD-v0.5"},
                ]
            ),
            ProviderField(
                name="voice",
                label="Voice / Voice URI",
                field_type="text",
                required=False,
                placeholder="speech:xxx:xxx or builtin voice id"
            ),
            ProviderField(
                name="response_format",
                label="Response Format",
                field_type="select",
                required=False,
                default="mp3",
                options=[
                    {"value": "mp3", "label": "mp3"},
                    {"value": "wav", "label": "wav"},
                    {"value": "opus", "label": "opus"},
                    {"value": "pcm", "label": "pcm"},
                ]
            ),
            ProviderField(
                name="speed",
                label="Speed",
                field_type="number",
                required=False,
                default=1.0,
                min_value=0.25,
                max_value=4.0
            ),
            ProviderField(
                name="gain",
                label="Gain (dB)",
                field_type="number",
                required=False,
                default=0.0,
                min_value=-10.0,
                max_value=10.0
            ),
            ProviderField(
                name="sample_rate",
                label="Sample Rate",
                field_type="number",
                required=False,
                default=32000,
                min_value=8000,
                max_value=48000
            ),
            ProviderField(
                name="timeout",
                label="Timeout (seconds)",
                field_type="number",
                required=False,
                default=120,
                min_value=10,
                max_value=600
            ),
        ]
    ),

    "minimax": ProviderDefinition(
        provider="minimax",
        display_name="MiniMax Audio",
        description="MiniMax TTS service",
        category=ApiCategory.TTS,
        website_url="https://www.minimaxi.com",
        icon="mic",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your MiniMax API key",
                sensitive=True
            ),
            ProviderField(
                name="model",
                label="Model",
                field_type="text",
                required=True,
                default="speech-01",
                placeholder="speech-01"
            ),
        ]
    ),

    "openai_tts": ProviderDefinition(
        provider="openai_tts",
        display_name="OpenAI TTS",
        description="OpenAI text-to-speech",
        category=ApiCategory.TTS,
        website_url="https://platform.openai.com",
        icon="mic",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your OpenAI API key",
                sensitive=True
            ),
            ProviderField(
                name="model",
                label="Model",
                field_type="select",
                required=True,
                default="tts-1",
                options=[
                    {"value": "tts-1", "label": "tts-1 (Faster)"},
                    {"value": "tts-1-hd", "label": "tts-1-hd (Higher Quality)"}
                ]
            ),
            ProviderField(
                name="voice",
                label="Voice",
                field_type="select",
                required=True,
                default="alloy",
                options=[
                    {"value": "alloy", "label": "Alloy"},
                    {"value": "echo", "label": "Echo"},
                    {"value": "fable", "label": "Fable"},
                    {"value": "onyx", "label": "Onyx"},
                    {"value": "nova", "label": "Nova"},
                    {"value": "shimmer", "label": "Shimmer"}
                ]
            ),
        ]
    ),

    "tts_custom": ProviderDefinition(
        provider="custom",
        display_name="Custom TTS API",
        description="Custom TTS API endpoint",
        category=ApiCategory.TTS,
        icon="mic",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=False,
                placeholder="Enter your API key (if required)",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                placeholder="https://api.example.com"
            ),
            ProviderField(
                name="model",
                label="Model",
                field_type="text",
                required=False,
                placeholder="Model name (optional)"
            ),
        ]
    ),

    # ==================== LLM Providers ====================
    "glm": ProviderDefinition(
        provider="glm",
        display_name="Zhipu GLM",
        description="Zhipu AI GLM language model",
        category=ApiCategory.LLM,
        website_url="https://open.bigmodel.cn",
        icon="brain",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your GLM API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                default="https://open.bigmodel.cn/api/paas/v4",
                placeholder="https://open.bigmodel.cn/api/paas/v4"
            ),
            ProviderField(
                name="model",
                label="Model",
                field_type="select",
                required=True,
                default="glm-4",
                options=[
                    {"value": "glm-4", "label": "GLM-4"},
                    {"value": "glm-4-flash", "label": "GLM-4-Flash (Faster)"},
                    {"value": "glm-4-plus", "label": "GLM-4-Plus"},
                ]
            ),
        ]
    ),

    "agnes": ProviderDefinition(
        provider="agnes",
        display_name="Agnes 2.0 Flash",
        description="Agnes OpenAI-compatible language model for scripts and agent workflows",
        category=ApiCategory.LLM,
        website_url="https://agnes-ai.com",
        icon="brain",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your Agnes API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                default="https://apihub.agnes-ai.com/v1",
                placeholder="https://apihub.agnes-ai.com/v1"
            ),
            ProviderField(
                name="model",
                label="Model",
                field_type="text",
                required=True,
                default="agnes-2.0-flash",
                placeholder="agnes-2.0-flash"
            ),
            ProviderField(
                name="temperature",
                label="Temperature",
                field_type="number",
                required=False,
                default=0.7,
                min_value=0,
                max_value=2
            ),
            ProviderField(
                name="max_tokens",
                label="Max Tokens",
                field_type="number",
                required=False,
                default=1024,
                min_value=1,
                max_value=8192
            ),
            ProviderField(
                name="timeout",
                label="Timeout (seconds)",
                field_type="number",
                required=False,
                default=60,
                min_value=10,
                max_value=300
            ),
        ]
    ),

    "openai": ProviderDefinition(
        provider="openai",
        display_name="OpenAI",
        description="OpenAI GPT models",
        category=ApiCategory.LLM,
        website_url="https://platform.openai.com",
        icon="brain",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your OpenAI API key",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                default="https://api.openai.com/v1",
                placeholder="https://api.openai.com/v1"
            ),
            ProviderField(
                name="model",
                label="Model",
                field_type="select",
                required=True,
                default="gpt-4o",
                options=[
                    {"value": "gpt-4o", "label": "GPT-4o"},
                    {"value": "gpt-4o-mini", "label": "GPT-4o Mini"},
                    {"value": "gpt-4-turbo", "label": "GPT-4 Turbo"},
                    {"value": "gpt-3.5-turbo", "label": "GPT-3.5 Turbo"},
                ]
            ),
        ]
    ),

    "gemini": ProviderDefinition(
        provider="gemini",
        display_name="Google Gemini",
        description="Google Gemini language model",
        category=ApiCategory.LLM,
        website_url="https://ai.google.dev",
        icon="brain",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your Google API key",
                sensitive=True
            ),
            ProviderField(
                name="model",
                label="Model",
                field_type="select",
                required=True,
                default="gemini-pro",
                options=[
                    {"value": "gemini-pro", "label": "Gemini Pro"},
                    {"value": "gemini-1.5-pro", "label": "Gemini 1.5 Pro"},
                    {"value": "gemini-1.5-flash", "label": "Gemini 1.5 Flash"},
                ]
            ),
        ]
    ),

    "baidu_wenxin": ProviderDefinition(
        provider="baidu_wenxin",
        display_name="Baidu Wenxin",
        description="Baidu Ernie language model",
        category=ApiCategory.LLM,
        website_url="https://cloud.baidu.com/product/wenxinworkshop",
        icon="brain",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="text",
                required=True,
                placeholder="Enter your Baidu API key",
                sensitive=True
            ),
            ProviderField(
                name="secret_key",
                label="Secret Key",
                field_type="password",
                required=True,
                placeholder="Enter your Baidu Secret key",
                sensitive=True
            ),
            ProviderField(
                name="model",
                label="Model",
                field_type="select",
                required=True,
                default="ernie-4.0",
                options=[
                    {"value": "ernie-4.0", "label": "ERNIE 4.0"},
                    {"value": "ernie-3.5", "label": "ERNIE 3.5"},
                    {"value": "ernie-speed", "label": "ERNIE Speed"},
                ]
            ),
        ]
    ),

    "kimi": ProviderDefinition(
        provider="kimi",
        display_name="Moonshot Kimi",
        description="Moonshot AI Kimi language model",
        category=ApiCategory.LLM,
        website_url="https://moonshot.cn",
        icon="brain",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=True,
                placeholder="Enter your Kimi API key",
                sensitive=True
            ),
            ProviderField(
                name="model",
                label="Model",
                field_type="select",
                required=True,
                default="moonshot-v1-8k",
                options=[
                    {"value": "moonshot-v1-8k", "label": "Moonshot V1 8K"},
                    {"value": "moonshot-v1-32k", "label": "Moonshot V1 32K"},
                    {"value": "moonshot-v1-128k", "label": "Moonshot V1 128K"},
                ]
            ),
        ]
    ),

    "llm_custom": ProviderDefinition(
        provider="custom",
        display_name="Custom OpenAI Compatible",
        description="Any OpenAI-compatible LLM API",
        category=ApiCategory.LLM,
        icon="brain",
        fields=[
            ProviderField(
                name="api_key",
                label="API Key",
                field_type="password",
                required=False,
                placeholder="Enter your API key (if required)",
                sensitive=True
            ),
            ProviderField(
                name="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                placeholder="https://api.example.com/v1"
            ),
            ProviderField(
                name="model",
                label="Model Name",
                field_type="text",
                required=True,
                placeholder="model-name"
            ),
        ]
    ),
}


def get_providers_by_category(category: ApiCategory) -> List[ProviderDefinition]:
    """Get all providers for a given category"""
    return [
        provider for provider in PROVIDER_DEFINITIONS.values()
        if provider.category == category
    ]


def get_provider_definition(
    provider: str,
    category: Optional[ApiCategory | str] = None
) -> Optional[ProviderDefinition]:
    """Get provider definition by provider name, optionally scoped by category."""
    # Fast path for exact key lookup (works for unique provider keys like "glm")
    direct = PROVIDER_DEFINITIONS.get(provider)
    if direct and category is None:
        return direct

    # Normalize category if provided
    category_enum: Optional[ApiCategory] = None
    if category is not None:
        if isinstance(category, ApiCategory):
            category_enum = category
        else:
            try:
                category_enum = ApiCategory(category)
            except ValueError:
                return None

    # Provider names like "custom" are shared across categories, so resolve by value
    matches = [p for p in PROVIDER_DEFINITIONS.values() if p.provider == provider]
    if category_enum is not None:
        for match in matches:
            if match.category == category_enum:
                return match
        return None

    if len(matches) == 1:
        return matches[0]

    return direct


def get_category_display_name(category: ApiCategory) -> str:
    """Get display name for a category"""
    names = {
        ApiCategory.AI_IMAGE: "AI Image Generation",
        ApiCategory.CLOUD_STORAGE: "Cloud Storage",
        ApiCategory.DIGITAL_HUMAN: "Digital Human Video",
        ApiCategory.TTS: "Text-to-Speech",
        ApiCategory.LLM: "Large Language Model",
    }
    return names.get(category, category.value)


def get_category_icon(category: ApiCategory) -> str:
    """Get icon name for a category"""
    icons = {
        ApiCategory.AI_IMAGE: "image",
        ApiCategory.CLOUD_STORAGE: "cloud",
        ApiCategory.DIGITAL_HUMAN: "video",
        ApiCategory.TTS: "mic",
        ApiCategory.LLM: "brain",
    }
    return icons.get(category, "settings")


def provider_to_dict(provider: ProviderDefinition) -> Dict[str, Any]:
    """Convert provider definition to dictionary for API response"""
    return {
        "provider": provider.provider,
        "display_name": provider.display_name,
        "description": provider.description,
        "category": provider.category.value,
        "website_url": provider.website_url,
        "icon": provider.icon,
        "fields": [
            {
                "name": field.name,
                "label": field.label,
                "type": field.field_type,
                "required": field.required,
                "default": field.default,
                "placeholder": field.placeholder,
                "description": field.description,
                "options": field.options,
                "sensitive": field.sensitive,
                "min_value": field.min_value,
                "max_value": field.max_value,
            }
            for field in provider.fields
        ]
    }
