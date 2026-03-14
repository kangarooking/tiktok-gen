# Security Policy

## Supported Scope

当前安全支持范围：
- `backend/` API 与鉴权逻辑
- `frontend/` 与后端交互的安全边界
- 第三方 API 配置与密钥处理逻辑

## Reporting a Vulnerability

请不要在公开 Issue 直接披露漏洞细节。  
建议通过私密渠道提交以下信息：

1. 漏洞类型与影响范围
2. 复现步骤（最小可复现）
3. 可能的利用条件
4. 修复建议（可选）

收到后会尽快确认并安排修复，修复完成后再公开披露。

## Secret Management Baseline

- 仅在 `.env` 中存放密钥，提交仓库时使用示例占位符
- 对 API Key 在日志与返回值中做掩码处理
- 不在前端代码中硬编码任何服务端密钥
