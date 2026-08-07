#!/usr/bin/env bash
# 构建 Docker 镜像：默认使用当前用户的 uid/gid，可用环境变量覆盖
#   UID=1234 GID=1234 ./deploy/build.sh
set -e
cd "$(dirname "$0")/.."

docker build -f deploy/Dockerfile \
    --build-arg UID="$(id -u)" \
    --build-arg GID="$(id -g)" \
    -t llmchat:latest \
    .

echo "镜像构建完成：llmchat:latest"
