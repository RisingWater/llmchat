"""视频生成服务：ComfyUI 生成视频 + ffmpeg 截帧/合并

当前状态：
- extract_last_frame / merge_videos 已实现（依赖容器内 ffmpeg）
- generate_video 尚未实现（ComfyUI MiniMax H3 工作流待接入），先抛 NotImplementedError，
  对应接口返回 501
"""

import subprocess
import uuid
from pathlib import Path

# 视频文件根目录（相对仓库根，gitignore 已排除 output/）
VIDEO_DIR = Path("output/videos")
FRAME_DIR = Path("output/frames")


def _run_ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", *args], check=True, capture_output=True)


def extract_last_frame(video_path: str | Path, out_path: str | Path | None = None) -> str:
    """截取视频最后一帧为 PNG，返回输出路径"""
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(out_path) if out_path else FRAME_DIR / f"frame_{uuid.uuid4().hex}.png"
    _run_ffmpeg("-sseof", "-0.1", "-i", str(video_path), "-frames:v", "1", str(out))
    return str(out)


def merge_videos(video_paths: list[str | Path], out_path: str | Path) -> str:
    """按顺序合并多个视频（concat demuxer，同编码直接 copy）"""
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    list_file = VIDEO_DIR / f"concat_{uuid.uuid4().hex}.txt"
    list_file.write_text("".join(f"file '{Path(p).resolve()}'\n" for p in video_paths), encoding="utf-8")
    try:
        _run_ffmpeg("-f", "concat", "-safe", "0", "-i", str(list_file),
                    "-c", "copy", str(out_path))
    finally:
        list_file.unlink(missing_ok=True)
    return str(out_path)


async def generate_video(conversation_id: int, prompt: str, first_frame_path: str | None) -> str:
    """生成一段视频（MiniMax H3 图生视频），返回视频文件路径

    TODO: 接入 ComfyUI（comfyui_gen.py 同款方案）：
      1. 上传首帧图到 ComfyUI（/upload/image）
      2. 提交 minimax_h3_i2v_workflow，轮询 /history
      3. 下载输出视频到 output/videos/
      4. 生成完成后调用方负责：截取最后一帧 + 与上一个视频合并
    """
    raise NotImplementedError("视频生成功能尚未实现")


def ensure_dirs() -> None:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
