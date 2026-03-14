#!/bin/bash

# TikTokGen Backend - 一键启动脚本
# 使用 tmux 分屏显示后端 API 和 Celery Worker 日志

SESSION_NAME="tiktokgen"
BACKEND_DIR="$(cd "$(dirname "$0")" && pwd)"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  TikTokGen Backend 一键启动脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查 tmux 是否安装
if ! command -v tmux &> /dev/null; then
    echo -e "${RED}错误: tmux 未安装${NC}"
    echo "请运行: brew install tmux"
    exit 1
fi

# 停止旧的服务
echo -e "${YELLOW}停止旧的服务...${NC}"
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "celery -A app.tasks worker" 2>/dev/null
sleep 2

# 删除旧的 tmux session
tmux kill-session -t $SESSION_NAME 2>/dev/null

# 创建新的 tmux session
echo -e "${GREEN}创建 tmux session: $SESSION_NAME${NC}"
tmux new-session -d -s $SESSION_NAME -n "Backend"

# 窗口 1: 后端 API (左侧大窗口)
tmux send-keys -t $SESSION_NAME "cd $BACKEND_DIR" C-m
tmux send-keys -t $SESSION_NAME "echo -e '\033[1;36m========== 后端 API 服务 ==========\033[0m'" C-m
tmux send-keys -t $SESSION_NAME "uvicorn app.main:app --reload --host 0.0.0.0 --port 3001" C-m

# 窗口 2: Celery Worker (右侧小窗口) - 分割垂直方向
tmux split-window -h -t $SESSION_NAME -p 40
tmux send-keys -t $SESSION_NAME "cd $BACKEND_DIR" C-m
tmux send-keys -t $SESSION_NAME "echo -e '\033[1;35m========== Celery Worker ==========\033[0m'" C-m
tmux send-keys -t $SESSION_NAME "celery -A app.tasks worker --loglevel=info --pool=solo" C-m

# 窗口 3: 终端/监控 (底部窗口)
tmux split-window -v -t $SESSION_NAME:0.0 -p 20
tmux send-keys -t $SESSION_NAME "cd $BACKEND_DIR" C-m
tmux send-keys -t $SESSION_NAME "clear" C-m
tmux send-keys -t $SESSION_NAME "echo -e '\033[1;33m========== 快捷命令 ==========\033[0m'" C-m
tmux send-keys -t $SESSION_NAME "echo '查看日志: Ctrl+B 然后按 方向键 切换窗口'" C-m
tmux send-keys -t $SESSION_NAME "echo '退出会话: Ctrl+B 然后按 d'" C-m
tmux send-keys -t $SESSION_NAME "echo '重新连接: tmux attach -t $SESSION_NAME'" C-m
tmux send-keys -t $SESSION_NAME "echo '停止服务: ./stop.sh'" C-m
tmux send-keys -t $SESSION_NAME "echo ''" C-m
tmux send-keys -t $SESSION_NAME "echo -e '\033[1;33m========== 服务状态 ==========\033[0m'" C-m
tmux send-keys -t $SESSION_NAME "watch -n 2 'echo \"=== 后端 API ===\" && curl -s http://localhost:3001/health && echo \"\" && echo \"=== Celery ===\" && ps aux | grep celery | grep -v grep | wc -l | xargs echo \"进程数:\"'" C-m

echo ""
echo -e "${GREEN}✓ 服务启动完成！${NC}"
echo ""
echo -e "${YELLOW}tmux 会话信息:${NC}"
echo "  会话名: $SESSION_NAME"
echo "  窗口布局:"
echo "    ┌──────────────────┬──────────────┐"
echo "    │                  │              │"
echo "    │   后端 API       │  Celery      │"
echo "    │   (左 60%)       │  Worker      │"
echo "    │                  │  (右 40%)    │"
echo "    ├──────────────────┴──────────────┤"
echo "    │                                 │"
echo "    │      监控/快捷命令               │"
echo "    │                                 │"
echo "    └─────────────────────────────────┘"
echo ""
echo -e "${YELLOW}快捷操作:${NC}"
echo "  查看日志: tmux attach -t $SESSION_NAME"
echo "  退出会话: 按 Ctrl+B 然后按 d (detach)"
echo "  停止服务: ./stop.sh"
echo ""
echo -e "${GREEN}正在自动连接到 tmux 会话...${NC}"
sleep 1
tmux attach-session -t $SESSION_NAME
