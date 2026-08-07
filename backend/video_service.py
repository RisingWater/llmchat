"""视频生成服务：ComfyUI（MiniMax H3 图生视频）生成 + ffmpeg 截帧/合并 + 落盘"""

import subprocess
import uuid
from pathlib import Path

# 视频文件根目录（相对仓库根，gitignore 已排除 output/）
VIDEO_DIR = Path("output/videos")
FRAME_DIR = Path("output/frames")


def ensure_dirs() -> None:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    FRAME_DIR.mkdir(parents=True, exist_ok=True)


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
    list_file.write_text(
        "".join(f"file '{Path(p).resolve().as_posix()}'\n" for p in video_paths),
        encoding="utf-8",
    )
    try:
        _run_ffmpeg("-f", "concat", "-safe", "0", "-i", str(list_file),
                    "-c", "copy", str(out_path))
    finally:
        list_file.unlink(missing_ok=True)
    return str(out_path)


async def generate_video_file(
    prompt: str,
    frame_path: str | Path,
    megapixels: float | None = None,
    steps: int | None = None,
    duration: float | None = None,
) -> tuple[str, str]:
    """MiniMax H3 图生视频：生成一段新视频并截取最后一帧

    返回 (视频文件路径, 最后一帧路径)；生成失败抛异常。
    """
    from backend.video_gen import generate_video  # 延迟导入，避免与模块名冲突

    ensure_dirs()
    frame_bytes = Path(frame_path).read_bytes()
    video_bytes = await generate_video(
        prompt, frame_bytes, megapixels=megapixels, steps=steps, duration=duration
    )
    if not video_bytes:
        raise RuntimeError("视频生成失败（ComfyUI 未返回视频数据）")

    video_path = VIDEO_DIR / f"{uuid.uuid4().hex}.mp4"
    video_path.write_bytes(video_bytes)

    last_frame = extract_last_frame(video_path)
    return str(video_path), last_frame