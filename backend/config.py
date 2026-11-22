import os
from dotenv import load_dotenv

from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

API_KEY = os.getenv("API_KEY", "")
API_BASE = os.getenv("API_BASE", "https://api.deepseek.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "admin")
JWT_SECRET = os.getenv("JWT_SECRET", API_KEY)  # 用 API_KEY 做 JWT 签名密钥

# ---- 模型档案 ----
# 本地 llama.cpp（OpenAI 兼容端点）
LOCAL_LLM_BASE = os.getenv("LOCAL_LLM_BASE", "http://192.168.1.181:9931/v1")
# 留空则运行时从 /v1/models 取第一个模型名
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "")
LOCAL_LLM_KEY = os.getenv("LOCAL_LLM_KEY", "")

# 上下文窗口（token）：本地 100K，DeepSeek 200K
LOCAL_CONTEXT_LIMIT = int(os.getenv("LOCAL_CONTEXT_LIMIT", "100000"))
DEEPSEEK_CONTEXT_LIMIT = int(os.getenv("DEEPSEEK_CONTEXT_LIMIT", "200000"))

# 单次输出上限（token）：会话设置里可调，但不能超过这里
# 本地不传 max_tokens 时 llama.cpp 按 n_predict=-1 无限生成，必须有上限
LOCAL_MAX_TOKENS = int(os.getenv("LOCAL_MAX_TOKENS", "32768"))
DEEPSEEK_MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", "8192"))

MODEL_PROFILES = {
    "deepseek": {
        "label": "DeepSeek",
        "base": API_BASE,
        "key": API_KEY,
        "model": MODEL_NAME,
        "context": DEEPSEEK_CONTEXT_LIMIT,
        "max_tokens": DEEPSEEK_MAX_TOKENS,
        "timeout": 300,
    },
    "local": {
        "label": "本地",
        "base": LOCAL_LLM_BASE,
        "key": LOCAL_LLM_KEY,
        "model": LOCAL_LLM_MODEL,
        "context": LOCAL_CONTEXT_LIMIT,
        "max_tokens": LOCAL_MAX_TOKENS,
        "timeout": 900,
    },
}

DEFAULT_MODEL = "deepseek"

# ComfyUI 图片生成配置
COMFYUI_BASE = os.getenv("COMFYUI_BASE", "http://192.168.1.181:8188")
# 文生图/图生图（z-image-turbo）工作流；其他 workflow 各用独立环境变量
COMFYUI_ZIMAGE_WORKFLOW = os.getenv("COMFYUI_ZIMAGE_WORKFLOW", "image_z_image_turbo.json")
# 图生视频（MiniMax H3）工作流
COMFYUI_MINIMAX_WORKFLOW = os.getenv("COMFYUI_MINIMAX_WORKFLOW", "minimax_h3_i2v_workflow.json")


def _video_file_server_base() -> str:
    """ComfyUI 同机的视频文件服务（file_server.py，8187 端口），从 COMFYUI_BASE 推导 host"""
    from urllib.parse import urlparse

    host = urlparse(COMFYUI_BASE).hostname or "127.0.0.1"
    return f"http://{host}:8187"


# 视频下载完成后，删除 ComfyUI 机器上对应的文件（腾磁盘空间）；空则跳过
COMFYUI_FILE_SERVER = os.getenv("COMFYUI_FILE_SERVER", _video_file_server_base())

# 微信通知（NAS 微信网关；WECHAT_WHO 为空则不发送）
WECHAT_SEND_URL = os.getenv("WECHAT_SEND_URL", "http://127.0.0.1:9020")
WECHAT_WHO = os.getenv("WECHAT_WHO", "")
WECHAT_WXNAME = os.getenv("WECHAT_WXNAME", "")
