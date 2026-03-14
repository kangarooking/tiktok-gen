# 数字人视频平台 - 后端API接口文档

## 📋 文档信息

| 项目 | 信息 |
|------|------|
| **API版本** | v1.0 |
| **基础URL** | `http://localhost:3001/api/v1` |
| **数据格式** | JSON |
| **认证方式** | Bearer Token (JWT) |
| **字符编码** | UTF-8 |

---

## 1. 通用规范

### 1.1 请求头

| Header | 说明 | 必填 |
|--------|------|------|
| `Content-Type` | `application/json` | ✅ |
| `Authorization` | `Bearer {token}` | 需认证接口必填 |
| `Accept-Language` | `zh-CN` / `en-US` | 可选 |

### 1.2 响应格式

**成功响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "timestamp": "2026-01-12T01:45:22+08:00"
}
```

**错误响应**:
```json
{
  "code": 40001,
  "message": "Invalid token",
  "error": "TokenExpiredError",
  "timestamp": "2026-01-12T01:45:22+08:00"
}
```

### 1.3 错误码定义

| 错误码 | HTTP状态 | 说明 |
|--------|----------|------|
| 200 | 200 | 成功 |
| 40001 | 401 | Token无效或过期 |
| 40003 | 403 | 权限不足 |
| 40004 | 404 | 资源不存在 |
| 40010 | 400 | 参数校验失败 |
| 40020 | 400 | 用量不足 |
| 50001 | 500 | 服务器内部错误 |
| 50002 | 503 | 第三方服务不可用 |

### 1.4 分页参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页数量，最大100 |

**分页响应**:
```json
{
  "data": {
    "list": [...],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  }
}
```

---

## 2. 认证模块 (Auth)

### 2.1 GitHub OAuth登录

获取GitHub授权URL，前端跳转进行OAuth认证。

**请求**:
```http
GET /auth/github
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "auth_url": "https://github.com/login/oauth/authorize?client_id=xxx&redirect_uri=xxx&scope=user:email"
  }
}
```

---

### 2.2 GitHub OAuth回调

处理GitHub OAuth回调，完成登录并返回JWT Token。

**请求**:
```http
POST /auth/github/callback
Content-Type: application/json

{
  "code": "github_oauth_code"
}
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | ✅ | GitHub返回的授权码 |

**响应**:
```json
{
  "code": 200,
  "message": "Login successful",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 604800,
    "user": {
      "id": "uuid",
      "username": "KangarooKing",
      "email": "king@example.com",
      "avatar_url": "https://github.com/avatars/xxx",
      "tier": "free",
      "created_at": "2026-01-12T01:45:22Z"
    }
  }
}
```

---

### 2.3 获取当前用户

获取当前登录用户信息。

**请求**:
```http
GET /auth/me
Authorization: Bearer {token}
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "id": "uuid",
    "username": "KangarooKing",
    "email": "king@example.com",
    "avatar_url": "https://github.com/avatars/xxx",
    "tier": "pro",
    "usage": {
      "used_minutes": 42,
      "total_minutes": 60,
      "reset_at": "2026-02-01T00:00:00Z"
    },
    "created_at": "2026-01-12T01:45:22Z"
  }
}
```

---

### 2.4 退出登录

使当前Token失效。

**请求**:
```http
POST /auth/logout
Authorization: Bearer {token}
```

**响应**:
```json
{
  "code": 200,
  "message": "Logout successful"
}
```

---

## 3. 用户模块 (Users)

### 3.1 更新用户信息

更新当前用户基本信息。

**请求**:
```http
PUT /users/profile
Authorization: Bearer {token}
Content-Type: application/json

{
  "username": "NewUsername",
  "email": "new@example.com"
}
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | ⚪ | 用户名，2-50字符 |
| email | string | ⚪ | 邮箱地址 |

**响应**:
```json
{
  "code": 200,
  "message": "Profile updated",
  "data": {
    "id": "uuid",
    "username": "NewUsername",
    "email": "new@example.com",
    "updated_at": "2026-01-12T01:45:22Z"
  }
}
```

---

### 3.2 获取用量统计

获取当前用户的用量统计信息。

**请求**:
```http
GET /users/usage
Authorization: Bearer {token}
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "tier": "pro",
    "billing_cycle": {
      "start": "2026-01-01T00:00:00Z",
      "end": "2026-02-01T00:00:00Z"
    },
    "usage": {
      "videos_generated": 15,
      "minutes_used": 42,
      "minutes_limit": 60,
      "storage_used_mb": 256,
      "storage_limit_mb": 1024
    },
    "history": [
      {
        "date": "2026-01-11",
        "videos": 3,
        "minutes": 8
      }
    ]
  }
}
```

---

## 4. 资产模块 (Assets)

### 4.1 获取资产列表

获取当前用户的资产列表，支持按类型筛选。

**请求**:
```http
GET /assets?type=avatar&page=1&page_size=20
Authorization: Bearer {token}
```

**Query参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | ⚪ | 资产类型: avatar/voice/script |
| is_system | boolean | ⚪ | 是否系统预设 |
| keyword | string | ⚪ | 搜索关键字 |
| page | int | ⚪ | 页码，默认1 |
| page_size | int | ⚪ | 每页数量，默认20 |

**响应**:
```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "id": "uuid",
        "type": "avatar",
        "title": "Professional Host (Sarah)",
        "is_system": true,
        "file_url": "https://oss.example.com/avatars/xxx.png",
        "preview_url": null,
        "metadata": {
          "tags": ["Professional", "News"],
          "gender": "female"
        },
        "created_at": "2026-01-10T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 5,
      "total_pages": 1
    }
  }
}
```

---

### 4.2 获取资产详情

获取单个资产详细信息。

**请求**:
```http
GET /assets/{asset_id}
Authorization: Bearer {token}
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "id": "uuid",
    "type": "voice",
    "title": "Warm Female Voice",
    "is_system": false,
    "file_url": "https://oss.example.com/voices/xxx.wav",
    "preview_url": "https://oss.example.com/voices/xxx_preview.mp3",
    "metadata": {
      "gender": "female",
      "tags": ["Warm", "Storytelling"],
      "duration_seconds": 5.2
    },
    "created_at": "2026-01-10T10:00:00Z",
    "updated_at": "2026-01-10T10:00:00Z"
  }
}
```

---

### 4.3 创建形象资产 (上传)

上传本地图片创建形象资产。

**请求**:
```http
POST /assets/avatars/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

title: My Custom Avatar
file: [binary image file]
tags: ["Custom", "Brand"]
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | ✅ | 资产名称，2-100字符 |
| file | file | ✅ | 图片文件，支持jpg/png/webp，最大10MB |
| tags | array | ⚪ | 标签数组 |

**响应**:
```json
{
  "code": 200,
  "message": "Avatar created",
  "data": {
    "id": "uuid",
    "type": "avatar",
    "title": "My Custom Avatar",
    "file_url": "https://oss.example.com/avatars/xxx.png",
    "metadata": {
      "tags": ["Custom", "Brand"],
      "width": 512,
      "height": 768
    },
    "created_at": "2026-01-12T01:45:22Z"
  }
}
```

---

### 4.4 创建形象资产 (AI生成)

使用AI根据提示词生成形象

**请求**:
```http
POST /assets/avatars/generate
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "AI Generated Host",
  "prompt": "一位穿着白色西装的亚洲女性，专业主持人形象，正面照，面带微笑",
  "reference_image_urls": [
    "https://example.com/ref1.jpg",
    "https://example.com/ref2.jpg"
  ]
}
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | ✅ | 资产名称 |
| prompt | string | ✅ | 生成提示词 |
| reference_image_urls | array | ⚪ | 参考图片URL，最多4张 |

**响应**:
```json
{
  "code": 200,
  "message": "Generation started",
  "data": {
    "id": "uuid",
    "type": "avatar",
    "title": "AI Generated Host",
    "status": "generating",
    "task_id": "generation_task_id",
    "created_at": "2026-01-12T01:45:22Z"
  }
}
```

---

### 4.5 创建音色资产 (上传)

上传音频样本创建音色资产。

**请求**:
```http
POST /assets/voices/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

title: My Voice Clone
file: [binary audio file]
gender: female
tags: ["Warm", "Professional"]
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | ✅ | 音色名称 |
| file | file | ✅ | 音频文件，支持mp3/wav/m4a，最大20MB |
| gender | string | ⚪ | 性别: male/female |
| tags | array | ⚪ | 风格标签 |

**响应**:
```json
{
  "code": 200,
  "message": "Voice asset created",
  "data": {
    "id": "uuid",
    "type": "voice",
    "title": "My Voice Clone",
    "file_url": "https://oss.example.com/voices/xxx.wav",
    "preview_url": "https://oss.example.com/voices/xxx_preview.mp3",
    "metadata": {
      "gender": "female",
      "tags": ["Warm", "Professional"],
      "duration_seconds": 15.3
    },
    "created_at": "2026-01-12T01:45:22Z"
  }
}
```

---

### 4.6 创建脚本资产

创建文本脚本资产。

**请求**:
```http
POST /assets/scripts
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Product Launch Hook",
  "content": "Stop scrolling! You won't believe what we just released. This tool changes everything about how you create content.",
  "tags": ["Marketing", "Hook"]
}
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | ✅ | 脚本名称 |
| content | string | ✅ | 脚本内容，最大5000字符 |
| tags | array | ⚪ | 标签 |

**响应**:
```json
{
  "code": 200,
  "message": "Script created",
  "data": {
    "id": "uuid",
    "type": "script",
    "title": "Product Launch Hook",
    "content": "Stop scrolling! ...",
    "metadata": {
      "tags": ["Marketing", "Hook"],
      "estimated_seconds": 12,
      "word_count": 28
    },
    "created_at": "2026-01-12T01:45:22Z"
  }
}
```

---

### 4.7 更新资产

更新资产信息。

**请求**:
```http
PUT /assets/{asset_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Updated Title",
  "metadata": {
    "tags": ["NewTag"]
  }
}
```

**响应**:
```json
{
  "code": 200,
  "message": "Asset updated",
  "data": {
    "id": "uuid",
    "title": "Updated Title",
    "updated_at": "2026-01-12T01:45:22Z"
  }
}
```

---

### 4.8 删除资产

删除用户自定义资产（系统预设不可删除）。

**请求**:
```http
DELETE /assets/{asset_id}
Authorization: Bearer {token}
```

**响应**:
```json
{
  "code": 200,
  "message": "Asset deleted"
}
```

---

## 5. 项目模块 (Projects)

### 5.1 获取项目列表

获取用户的视频项目列表。

**请求**:
```http
GET /projects?status=completed&page=1&page_size=20
Authorization: Bearer {token}
```

**Query参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | ⚪ | 状态筛选: pending/generating_audio/generating_video/completed/failed |
| page | int | ⚪ | 页码 |
| page_size | int | ⚪ | 每页数量 |

**响应**:
```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "id": "uuid",
        "title": "Q4 Marketing Campaign",
        "status": "completed",
        "thumbnail_url": "https://oss.example.com/thumbnails/xxx.jpg",
        "video_url": "https://oss.example.com/videos/xxx.mp4",
        "duration_seconds": 32,
        "resolution": "480p",
        "created_at": "2026-01-10T10:00:00Z",
        "completed_at": "2026-01-10T10:01:30Z"
      },
      {
        "id": "uuid2",
        "title": "TikTok Viral Hook #3",
        "status": "generating_video",
        "thumbnail_url": null,
        "video_url": null,
        "progress": 65,
        "created_at": "2026-01-12T01:40:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 15,
      "total_pages": 1
    }
  }
}
```

---

### 5.2 获取项目详情

获取单个项目的详细信息。

**请求**:
```http
GET /projects/{project_id}
Authorization: Bearer {token}
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "id": "uuid",
    "title": "Q4 Marketing Campaign",
    "status": "completed",
    "thumbnail_url": "https://oss.example.com/thumbnails/xxx.jpg",
    "video_url": "https://oss.example.com/videos/xxx.mp4",
    "audio_url": "https://oss.example.com/audio/xxx.mp3",
    "duration_seconds": 32,
    "resolution": "480p",
    "assets": {
      "avatar": {
        "id": "avatar_uuid",
        "title": "Professional Host",
        "file_url": "https://..."
      },
      "voice": {
        "id": "voice_uuid",
        "title": "Warm Female",
        "file_url": "https://..."
      },
      "script": {
        "id": "script_uuid",
        "title": "Product Launch Hook",
        "content": "Stop scrolling! ..."
      }
    },
    "config": {
      "emotion": "professional",
      "performance_prompt": "Natural smile, sincere eye contact"
    },
    "created_at": "2026-01-10T10:00:00Z",
    "completed_at": "2026-01-10T10:01:30Z"
  }
}
```

---

### 5.3 创建视频生成任务

提交新的视频生成任务。

**请求**:
```http
POST /projects
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "New Marketing Video",
  "avatar_id": "avatar_uuid",
  "voice_id": "voice_uuid",
  "script_id": "script_uuid",
  "emotion": "professional",
  "performance_prompt": "Natural smile with confident eye contact",
  "resolution": "480p"
}
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | ⚪ | 项目标题，默认自动生成 |
| avatar_id | uuid | ✅ | 形象资产ID |
| voice_id | uuid | ✅ | 音色资产ID |
| script_id | uuid | ⚪ | 脚本资产ID (与script_content二选一) |
| script_content | string | ⚪ | 自定义脚本文本 (与script_id二选一) |
| emotion | string | ⚪ | 情绪风格: happy/professional/gentle/excited |
| performance_prompt | string | ⚪ | 表演提示词 |
| resolution | string | ⚪ | 分辨率: 480p/720p，默认480p |

**响应**:
```json
{
  "code": 200,
  "message": "Project created, generation started",
  "data": {
    "id": "uuid",
    "title": "New Marketing Video",
    "status": "pending",
    "estimated_seconds": 45,
    "created_at": "2026-01-12T01:45:22Z"
  }
}
```

---

### 5.4 获取项目状态

获取项目的实时状态和进度。

**请求**:
```http
GET /projects/{project_id}/status
Authorization: Bearer {token}
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "id": "uuid",
    "status": "generating_video",
    "progress": 65,
    "current_step": "数字人视频合成中",
    "steps": [
      { "name": "任务排队", "status": "completed" },
      { "name": "语音合成", "status": "completed" },
      { "name": "视频生成", "status": "in_progress" },
      { "name": "后处理", "status": "pending" }
    ],
    "estimated_remaining_seconds": 15,
    "updated_at": "2026-01-12T01:46:00Z"
  }
}
```

---

### 5.5 删除项目

删除项目及其关联文件。

**请求**:
```http
DELETE /projects/{project_id}
Authorization: Bearer {token}
```

**响应**:
```json
{
  "code": 200,
  "message": "Project deleted"
}
```

---

## 6. 生成模块 (Generation)

### 6.1 语音合成预览

合成音频预览，不保存，用于创作页面试听。

**请求**:
```http
POST /generation/audio-preview
Authorization: Bearer {token}
Content-Type: application/json

{
  "voice_id": "voice_uuid",
  "text": "Stop scrolling! You won't believe this.",
  "emotion": "excited"
}
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| voice_id | uuid | ✅ | 音色资产ID |
| text | string | ✅ | 合成文本，最大500字符 |
| emotion | string | ⚪ | 情绪: happy/professional/gentle/excited |

**响应**:
```json
{
  "code": 200,
  "data": {
    "audio_url": "https://oss.example.com/temp/preview_xxx.mp3",
    "duration_seconds": 3.2,
    "expires_in": 300
  }
}
```

---

### 6.2 AI生成脚本

使用大语言模型生成营销脚本。

**请求**:
```http
POST /generation/script
Authorization: Bearer {token}
Content-Type: application/json

{
  "product_name": "智能手表 Pro",
  "product_description": "具有心率监测、GPS定位、7天续航的智能手表",
  "target_audience": "25-40岁白领人群",
  "tone": "professional",
  "duration_seconds": 30
}
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| product_name | string | ✅ | 产品名称 |
| product_description | string | ✅ | 产品描述 |
| target_audience | string | ⚪ | 目标人群 |
| tone | string | ⚪ | 风格: funny/professional/emotional |
| duration_seconds | int | ⚪ | 期望时长，默认30秒 |

**响应**:
```json
{
  "code": 200,
  "data": {
    "scripts": [
      {
        "content": "你是否还在为...",
        "estimated_seconds": 28,
        "word_count": 85
      },
      {
        "content": "听说了吗？...",
        "estimated_seconds": 32,
        "word_count": 96
      }
    ]
  }
}
```

---

## 7. 文件上传模块 (Upload)

### 7.1 获取上传凭证

获取阿里云OSS直传凭证。

**请求**:
```http
POST /upload/presign
Authorization: Bearer {token}
Content-Type: application/json

{
  "file_name": "avatar.png",
  "file_type": "image/png",
  "file_size": 1024000,
  "category": "avatar"
}
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file_name | string | ✅ | 文件名 |
| file_type | string | ✅ | MIME类型 |
| file_size | int | ✅ | 文件大小(bytes) |
| category | string | ✅ | 类别: avatar/voice/script/temp |

**响应**:
```json
{
  "code": 200,
  "data": {
    "upload_url": "https://your-bucket.oss-cn-beijing.aliyuncs.com",
    "key": "uploads/avatars/2026/01/uuid.png",
    "policy": "eyJleHBpcmF0aW9uIjoiMjAyNi...",
    "signature": "xxx",
    "access_key_id": "LTAI...",
    "callback": "https://api.example.com/upload/callback",
    "file_url": "https://your-bucket.oss-cn-beijing.aliyuncs.com/uploads/avatars/2026/01/uuid.png",
    "expires_in": 3600
  }
}
```

---

### 7.2 上传回调确认

OSS上传完成后的回调接口（OSS调用）。

**请求**:
```http
POST /upload/callback
Content-Type: application/json

{
  "key": "uploads/avatars/2026/01/uuid.png",
  "size": 1024000,
  "etag": "xxx"
}
```

**响应**:
```json
{
  "code": 200,
  "message": "Upload confirmed"
}
```

---

## 8. 系统模块 (System)

### 8.1 系统健康检查

检查系统及依赖服务状态。

**请求**:
```http
GET /system/health
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "environment": "production",
    "services": {
      "database": "healthy",
      "redis": "healthy",
      "oss": "healthy",
      "tts_api": "healthy",
      "video_api": "healthy"
    },
    "timestamp": "2026-01-12T01:45:22Z"
  }
}
```

---

### 8.2 获取系统配置

获取前端需要的系统配置。

**请求**:
```http
GET /system/config
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "max_upload_size_mb": 20,
    "supported_image_formats": ["jpg", "jpeg", "png", "webp"],
    "supported_audio_formats": ["mp3", "wav", "m4a"],
    "max_script_length": 5000,
    "max_video_duration_seconds": 600,
    "resolutions": ["480p", "720p"],
    "tiers": {
      "free": {
        "minutes_per_month": 10,
        "storage_mb": 100
      },
      "pro": {
        "minutes_per_month": 60,
        "storage_mb": 1024
      }
    }
  }
}
```

---

## 9. WebSocket接口

### 9.1 项目状态实时推送

订阅项目生成状态的实时更新。

**连接**:
```
wss://api.example.com/ws?token={jwt_token}
```

**订阅消息**:
```json
{
  "type": "subscribe",
  "channel": "project_status",
  "project_id": "uuid"
}
```

**推送消息**:
```json
{
  "type": "project_status",
  "data": {
    "project_id": "uuid",
    "status": "generating_video",
    "progress": 80,
    "current_step": "视频渲染中",
    "timestamp": "2026-01-12T01:46:00Z"
  }
}
```

**完成消息**:
```json
{
  "type": "project_completed",
  "data": {
    "project_id": "uuid",
    "status": "completed",
    "video_url": "https://...",
    "thumbnail_url": "https://...",
    "duration_seconds": 32
  }
}
```

---

## 10. 附录

### 10.1 状态枚举

**ProjectStatus**:
| 值 | 说明 |
|----|------|
| pending | 等待处理 |
| generating_audio | 音频生成中 |
| generating_video | 视频生成中 |
| completed | 已完成 |
| failed | 失败 |

**AssetType**:
| 值 | 说明 |
|----|------|
| avatar | 形象 |
| voice | 音色 |
| script | 脚本 |

**UserTier**:
| 值 | 说明 |
|----|------|
| free | 免费版 |
| pro | 专业版 |
| enterprise | 企业版 |

### 10.2 Rate Limiting

| 接口类型 | 限制 |
|----------|------|
| 普通接口 | 100次/分钟 |
| 生成类接口 | 10次/分钟 |
| 上传接口 | 20次/分钟 |

超过限制返回:
```json
{
  "code": 42901,
  "message": "Rate limit exceeded",
  "retry_after": 30
}
```
