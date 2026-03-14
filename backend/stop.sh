#!/bin/bash

# TikTokGen Backend - 一键停止脚本

SESSION_NAME="tiktokgen"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  TikTokGen Backend 停止脚本${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# 停止 tmux session
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo -e "${YELLOW}停止 tmux session: $SESSION_NAME${NC}"
    tmux kill-session -t $SESSION_NAME
    echo -e "${GREEN}✓ tmux session 已停止${NC}"
else
    echo -e "${YELLOW}tmux session 不存在${NC}"
fi

# 停止后端进程
echo -e "${YELLOW}停止后端服务...${NC}"
pkill -f "uvicorn app.main:app" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 后端 API 已停止${NC}"
else
    echo -e "${YELLOW}后端 API 未运行${NC}"
fi

# 停止 Celery worker
pkill -f "celery -A app.tasks worker" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Celery Worker 已停止${NC}"
else
    echo -e "${YELLOW}Celery Worker 未运行${NC}"
fi

echo ""
echo -e "${GREEN}✓ 所有服务已停止${NC}"
echo ""
