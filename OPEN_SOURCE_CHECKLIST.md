# Open Source 发布检查清单

## 必须补充

- `README.md`：项目简介、架构、快速启动、Docker 部署
- `LICENSE`：开源许可证（当前为 Apache-2.0）
- `CONTRIBUTING.md`：贡献流程与提交规范
- `SECURITY.md`：漏洞上报与密钥管理要求
- `.env.example` / `backend/.env.example` / `frontend/.env.example`

## 不应上传（含敏感信息）

- `backend/.env`
- `frontend/.env.local`
- `数据库信息.md`
- `github-Oauth配置.md`
- `docs/Redis信息.md`
- `docs/产品需求文档PRD.md`
- `docs/技术选型文档.md`
- `index-tts-api.md`
- `大模型API.md`
- `图片生成（Banana Pro）API.md`
- `数字人生成API.md`

> 以上文件已在 `.gitignore` 中默认忽略。若需公开，请先脱敏。

## 发布前最后检查

1. 全仓扫描密钥（`api_key` / `secret` / `sk-` / `Bearer`）
2. 确认所有示例配置均为占位符
3. `docker compose config` 校验通过
4. `docker compose up -d --build` 可启动
5. 前端与后端健康检查通过（`/health`、`/docs`）
