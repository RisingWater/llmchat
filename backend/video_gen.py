"""异步视频生成（MiniMax H3 图生视频）— 返回视频文件数据"""
import asyncio
import base64
from pathlib import Path

from backend.config import COMFYUI_BASE, COMFYUI_MINIMAX_WORKFLOW


async def generate_video(prompt: str, first_frame: bytes) -> bytes | None:
    """调用 ComfyUI 生成图生视频，返回视频字节。失败返回 None。

    first_frame — 首帧图片字节（内部转 base64 传入工作流）
    """
    try:
        return await asyncio.to_thread(_run_comfyui, prompt, first_frame)
    except Exception as e:
        print(f"[VIDEO] 生成失败: {e}", flush=True)
        return None


def _run_comfyui(prompt: str, first_frame: bytes) -> bytes:
    import sys
    root = str(Path(__file__).resolve().parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)

    from comfyui_video_gen import ComfyUIVideoGenerator

    # 图片转 base64 传入工作流
    image_b64 = base64.b64encode(first_frame).decode("ascii")

    gen = ComfyUIVideoGenerator(
        workflow=COMFYUI_MINIMAX_WORKFLOW,
        base_url=COMFYUI_BASE,
        output_dir=str(Path(root) / "output"),
    )
    # 生成视频到本地临时路径
    local_path = gen.generate(prompt, image_b64)
    # 读入内存
    data = Path(local_path).read_bytes()
    # 删除临时文件
    try:
        Path(local_path).unlink()
    except Exception:
        pass
    return data