"""异步图片生成 — 返回图片字节数据"""
import asyncio
from pathlib import Path

from backend.config import COMFYUI_BASE, COMFYUI_WORKFLOW


async def generate_image(prompt: str) -> bytes | None:
    """调用 ComfyUI 生成图片，返回图片字节。失败返回 None。"""
    try:
        return await asyncio.to_thread(_run_comfyui, prompt)
    except Exception as e:
        print(f"[IMG] 生成失败: {e}", flush=True)
        return None


def _run_comfyui(prompt: str) -> bytes:
    import sys
    root = str(Path(__file__).resolve().parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)

    from comfyui_gen import ComfyUIImageGenerator

    gen = ComfyUIImageGenerator(
        workflow=COMFYUI_WORKFLOW,
        base_url=COMFYUI_BASE,
        output_dir=str(Path(root) / "output"),
    )
    # 生成图片到本地临时路径
    local_path = gen.generate(prompt)
    # 读入内存
    data = Path(local_path).read_bytes()
    # 删除临时文件
    try:
        Path(local_path).unlink()
    except Exception:
        pass
    return data
