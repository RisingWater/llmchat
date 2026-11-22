#!/usr/bin/env bash
# 启动容器：将项目目录挂载到 /workdir，映射 8000 端口，容器内执行 /workdir/deploy/start.sh
# 可自定义端口：PORT=9000 ./deploy/run_docker.sh
set -e
cd "$(dirname "$0")/.."

PORT="${PORT:-3210}"

# 同名容器已存在则先删除
docker rm -f llmc 2>/dev/null || true

docker run -it -d \
    --name llmc \
    -p "${PORT}:8000" \
    -v "$(pwd):/workdir" \
    llmchat:latest

echo "容器已启动：http://127.0.0.1:${PORT}"
echo "查看日志：docker logs -f llmchat"
