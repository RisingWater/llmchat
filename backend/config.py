import os
from dotenv import load_dotenv

from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

API_KEY = os.getenv("API_KEY", "")
API_BASE = os.getenv("API_BASE", "https://api.deepseek.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "admin")
JWT_SECRET = os.getenv("JWT_SECRET", API_KEY)  # 用 API_KEY 做 JWT 签名密钥

# ComfyUI 图片生成配置
COMFYUI_BASE = os.getenv("COMFYUI_BASE", "http://127.0.0.1:8188")
# 文生图/图生图（z-image-turbo）工作流；其他 workflow 各用独立环境变量
COMFYUI_ZIMAGE_WORKFLOW = os.getenv("COMFYUI_ZIMAGE_WORKFLOW", "image_z_image_turbo.json")
# 图生视频（MiniMax H3）工作流
COMFYUI_MINIMAX_WORKFLOW = os.getenv("COMFYUI_MINIMAX_WORKFLOW", "minimax_h3_i2v_workflow.json")

# 微信通知（NAS 微信网关；WECHAT_WHO 为空则不发送）
WECHAT_SEND_URL = os.getenv("WECHAT_SEND_URL", "http://127.0.0.1:9020")
WECHAT_WHO = os.getenv("WECHAT_WHO", "")
WECHAT_WXNAME = os.getenv("WECHAT_WXNAME", "")
