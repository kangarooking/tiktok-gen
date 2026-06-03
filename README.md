# TikTokGen

English version: [README.en.md](README.en.md)

AI 营销短视频生成平台：选择形象、音色、文案后，自动完成语音合成与视频生成。

## 核心能力

- 资产管理：形象 / 音色 / 文案
- 极速创作：音色克隆、情绪控制、预读试听
- 多渠道配置：TTS、数字人、云存储、LLM
- 异步任务：Celery + Redis 处理生成流程

## 技术栈

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + SQLAlchemy + Celery
- Infra: PostgreSQL + Redis + Docker Compose

## 一键部署（Docker Compose）

```bash
cp .env.example .env
docker compose up -d
```

数据库结构文件位于 `database/schema.sql`。首次创建 PostgreSQL 数据卷时，Compose 会自动导入该 schema；如果你使用外部数据库，也可以手动导入：

```bash
psql "$DATABASE_URL" -f database/schema.sql
```

启动后访问：
- 前端：`http://localhost:3000`
- 后端：`http://localhost:3001`
- API 文档：`http://localhost:3001/docs`

如端口冲突，可在 `.env` 调整 `FRONTEND_PORT`、`BACKEND_PORT`，并同步设置 `VITE_API_URL`。

停止：

```bash
docker compose down
```

## Docker Hub 发布版部署

发布版 `docker-compose.yml` 使用预构建镜像（无需本地构建）。

```bash
cp .env.example .env
# 默认即使用 kangarooking/tiktokgen-* :v1.0.0
# 如需切换镜像版本，再修改 .env: DOCKERHUB_NAMESPACE / IMAGE_TAG
docker compose up -d
```

如果你是项目维护者，推送镜像到 Docker Hub：

```bash
# 先 docker login
./scripts/push_dockerhub.sh <dockerhub_namespace> <tag>
```

开发时如需本地构建版编排文件，请使用 `docker-compose.dev.yml`。

## 本地开发（不使用 Docker）

后端：

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
python init_db.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 3001
```

Worker（新终端）：

```bash
cd backend
celery -A app.tasks worker --loglevel=info --pool=solo
```

前端：

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

## 目录结构

```text
.
├── frontend/          # React 前端
├── backend/           # FastAPI + Celery 后端
├── database/          # PostgreSQL schema
├── docs/              # 业务与接口文档
├── docker-compose.yml
└── AGENTS.md
```

## 开源前注意

- 不要提交真实密钥：`.env`、OAuth secret、云厂商 AK/SK
- `backend/.env.example` 与 `.env.example` 只保留占位符
- 参考 `SECURITY.md` 与 `CONTRIBUTING.md`

## License

Apache-2.0
