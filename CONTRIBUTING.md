# Contributing

感谢你对项目的贡献。

## 开发前准备

1. Fork 并创建功能分支：`feat/xxx`、`fix/xxx`
2. 安装依赖：
   - 后端：`cd backend && pip install -r requirements.txt`
   - 前端：`cd frontend && npm install`
3. 复制环境变量模板：
   - `cp backend/.env.example backend/.env`
   - `cp frontend/.env.example frontend/.env.local`

## 提交规范

- 使用 Conventional Commits：`feat(scope): ...`、`fix(scope): ...`、`docs: ...`
- 单个提交只做一类事情（不要把重构和功能混在一起）
- 提交前确保：
  - 前端构建通过：`cd frontend && npm run build`
  - 后端可启动：`cd backend && uvicorn app.main:app --host 0.0.0.0 --port 3001`

## Pull Request 要求

- 说明变更目的、核心实现、验证步骤
- 标注影响范围（frontend/backend/docs）
- 如果是 UI 变更，请附截图
- 如果改动了配置项，请同步更新 `backend/.env.example` 或 `frontend/.env.example`

## 安全要求

- 禁止提交真实密钥、口令、数据库地址、OAuth Secret
- 禁止提交本地 `.env` 文件、导出的生产数据和日志快照
