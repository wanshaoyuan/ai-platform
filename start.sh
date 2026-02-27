#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"

echo "=============================="
echo "   AI 中台 - 一键启动脚本"
echo "=============================="

# ---- 1. 后端虚拟环境 ----
if [ ! -d "$VENV_DIR" ]; then
  echo "[1/4] 创建 Python 虚拟环境..."
  python3 -m venv "$VENV_DIR"
fi

echo "[2/4] 安装后端依赖..."
"$VENV_DIR/bin/pip" install -q --upgrade pip
"$VENV_DIR/bin/pip" install -q -r "$BACKEND_DIR/requirements.txt"

# ---- 2. 前端依赖 ----
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "[3/4] 安装前端依赖（首次）..."
  cd "$FRONTEND_DIR" && npm install --silent
fi

# ---- 3. 并发启动 ----
echo "[4/4] 启动服务..."
echo ""
echo "  后端 API :  http://127.0.0.1:8000"
echo "  前端页面 :  http://localhost:5173"
echo "  API 文档 :  http://127.0.0.1:8000/api/docs"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo ""

# 启动后端
cd "$BACKEND_DIR"
"$VENV_DIR/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# 启动前端
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

# 捕获中断信号，一并停止
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Services stopped.'" INT TERM

wait
