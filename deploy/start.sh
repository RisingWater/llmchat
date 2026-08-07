#!/usr/bin/env bash
# 容器启动脚本：拉取最新代码 → 创建 venv → 安装依赖 → 编译前端 → 启动后端
# 由 Dockerfile 的 CMD 在容器启动时执行（挂载的项目根目录 /workdir 中）
set -e

echo "[start] 1/5 拉取最新代码..."
cd /workdir
# 部署机器代码可能不是最新，先更新（拉取失败不阻塞启动）
if GIT_TERMINAL_PROMPT=0 git pull --ff-only; then
    echo "[start] 代码已更新"
else
    echo "[start] 警告：git pull 失败，使用现有代码继续启动"
fi

echo "[start] 2/5 创建 Python 虚拟环境并安装依赖..."
cd /workdir
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt

echo "[start] 3/5 安装前端依赖..."
cd /workdir/frontend
bun install

echo "[start] 4/5 编译前端..."
bun run build

echo "[start] 5/5 启动后端服务..."
cd /workdir
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
