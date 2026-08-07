# 运行时环境镜像 —— 仅提供工具链，不包含项目代码
# 代码由 run_docker.sh 挂载到 /workdir，启动时执行 /workdir/deploy/start.sh
FROM ubuntu:24.04

# ---- 构建参数 ----
# UID/GID：容器内运行用户与宿主机构建者一致（build.sh 默认传入当前用户），
# 保证挂载目录内生成的文件（chat.db/.venv/node_modules/dist）权限正确
ARG UID=1000
ARG GID=1000
# Node LTS 版本（Vite 8 要求 node >= 22.12，apt 自带的 nodejs 18 太旧）
ARG NODE_VERSION=22.14.0
# app 用户密码（sudo 提权用）
ARG APP_PASSWORD=centerm

# ---- apt 换阿里源（ubuntu 24.04 为 deb822 格式 /etc/apt/sources.list.d/ubuntu.sources）----
# 基础镜像不带 ca-certificates，先用 http 源完成安装，避免 HTTPS 证书校验失败
RUN sed -i -E \
    's|http://archive\.ubuntu\.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g; s|http://security\.ubuntu\.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g' \
    /etc/apt/sources.list.d/ubuntu.sources

# ---- 安装基础软件（vim 编辑文件，sudo 提权，ffmpeg 用于后续视频拼接，git 用于启动时拉取最新代码）----
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    xz-utils \
    git \
    vim \
    sudo \
    python3 \
    python3-venv \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# ---- pip 换阿里源 ----
RUN printf '[global]\nindex-url = https://mirrors.aliyun.com/pypi/simple/\n' > /etc/pip.conf

# ---- Node 22 + npm（npmmirror 二进制包）----
RUN curl -fsSL "https://npmmirror.com/mirrors/node/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
        -o /tmp/node.tar.xz \
    && tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 \
    && rm /tmp/node.tar.xz \
    && node -v && npm -v

# ---- 运行用户：uid/gid 与宿主机一致 ----
# ubuntu 基础镜像自带 uid/gid 1000 的 ubuntu 用户，与其冲突时复用并改名为 app
RUN if getent passwd "${UID}" > /dev/null 2>&1; then \
        usermod -l app -s /bin/bash -d /home/app "$(getent passwd "${UID}" | cut -d: -f1)" \
        && mkdir -p /home/app && chown -R "${UID}:${GID}" /home/app; \
    else \
        if ! getent group "${GID}" > /dev/null 2>&1; then groupadd -g "${GID}" app; fi \
        && useradd -m -u "${UID}" -g "${GID}" -s /bin/bash app; \
    fi \
    && usermod -aG sudo app \
    && echo "app:${APP_PASSWORD}" | chpasswd

# ---- npm/bun 换阿里源（app 用户的 ~/.npmrc 同时被 bun 读取）----
RUN npm config set registry https://registry.npmmirror.com -g \
    && echo 'registry=https://registry.npmmirror.com' > /home/app/.npmrc \
    && npm install -g bun \
    && bun --version

# ---- 工作目录（挂载点）----
RUN mkdir -p /workdir && chown "${UID}:${GID}" /workdir
WORKDIR /workdir

USER app

# 启动时执行挂载进来的项目启动脚本（挂载目录必须包含 deploy/start.sh）
CMD ["/bin/bash", "/workdir/deploy/start.sh"]
