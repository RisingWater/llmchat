"""视频生成服务：ComfyUI（MiniMax H3 图生视频）生成 + ffmpeg 截帧/合并 + 落盘

文件按会话分目录：output/{会话ID}_{会话名}/videos 与 .../frames
成片统一为 videos/merged.mp4（只保留一份，回退时重新拼接）
"""

import re
import subprocess
import uuid
from pathlib import Path

# 输出根目录（相对仓库根，gitignore 已排除 output/）
OUTPUT_DIR = Path("output")


def _safe_name(name: str) -> str:
    """文件夹名清洗：去掉 Windows 非法字符与空白，空则用占位"""
    name = re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("._ ")
    return name or "conv"


def conversation_dirs(conv_id: int, title: str = "") -> tuple[Path, Path]:
    """会话的输出目录：output/{conv_id}_{标题}/videos 与 .../frames

    带 ID 前缀：会话改名后目录不变，同标题会话不冲突
    """
    folder = OUTPUT_DIR / f"{conv_id}_{_safe_name(title)}"
    return folder / "videos", folder / "frames"


def ensure_dirs(conv_id: int | None = None, title: str = "") -> None:
    """创建输出目录；不传会话参数时只创建 output/"""
    if conv_id is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        return
    video_dir, frame_dir = conversation_dirs(conv_id, title)
    video_dir.mkdir(parents=True, exist_ok=True)
    frame_dir.mkdir(parents=True, exist_ok=True)


def _run_ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", *args], check=True, capture_output=True)


def extract_last_frame(video_path: str | Path, out_path: str | Path) -> str:
    """截取视频最后一帧为 PNG，返回输出路径"""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    _run_ffmpeg("-sseof", "-0.1", "-i", str(video_path), "-frames:v", "1", str(out))
    return str(out)


def merge_videos(video_paths: list[str | Path], out_path: str | Path) -> str:
    """按顺序合并多个视频（concat demuxer，同编码直接 copy）"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    list_file = out_path.parent / f"concat_{uuid.uuid4().hex}.txt"
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


def merged_path(video_dir: Path) -> Path:
    """会话成片路径（唯一）"""
    return video_dir / "merged.mp4"


def _replace_with_tmp(target: Path, build) -> str:
    """在 target 同目录写临时文件后原子替换，避免边读边写损坏"""
    tmp = target.with_name(f"{target.stem}_tmp_{uuid.uuid4().hex}{target.suffix}")
    try:
        build(tmp)
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)
    return str(target)


def append_merged(prev_merged: str | Path, new_video: str | Path, video_dir: Path) -> str:
    """新片段拼到成片末尾（覆盖 merged.mp4）"""
    return _replace_with_tmp(
        merged_path(video_dir),
        lambda tmp: merge_videos([prev_merged, new_video], tmp),
    )


def rebuild_merged(segment_paths: list[str | Path], video_dir: Path) -> str | None:
    """把所有片段重新拼成成片；无片段时删除成片"""
    out = merged_path(video_dir)
    if not segment_paths:
        out.unlink(missing_ok=True)
        return None
    return _replace_with_tmp(out, lambda tmp: merge_videos(segment_paths, tmp))


def _strip_audio(in_path: Path, out_path: Path) -> None:
    """去掉音轨（视频流直接 copy）"""
    _run_ffmpeg("-i", str(in_path), "-c:v", "copy", "-an", str(out_path))


async def generate_video_file(
    prompt: str,
    frame_path: str | Path,
    *,
    megapixels: float | None = None,
    steps: int | None = None,
    duration: float | None = None,
    video_dir: Path | None = None,
    frame_dir: Path | None = None,
    keep_audio: bool = True,
) -> tuple[str, str]:
    """MiniMax H3 图生视频：生成一段新视频并截取最后一帧

    返回 (视频文件路径, 最后一帧路径)；生成失败抛异常。
    """
    from backend.video_gen import generate_video  # 延迟导入，避免与模块名冲突

    video_dir = video_dir or OUTPUT_DIR / "videos"
    frame_dir = frame_dir or OUTPUT_DIR / "frames"
    video_dir.mkdir(parents=True, exist_ok=True)
    frame_dir.mkdir(parents=True, exist_ok=True)

    frame_bytes = Path(frame_path).read_bytes()
    video_bytes = await generate_video(
        prompt, frame_bytes, megapixels=megapixels, steps=steps, duration=duration
    )
    if not video_bytes:
        raise RuntimeError("视频生成失败（ComfyUI 未返回视频数据）")

    video_path = video_dir / f"{uuid.uuid4().hex}.mp4"
    video_path.write_bytes(video_bytes)
    # 不保留音频：存盘前去音轨
    if not keep_audio:
        _replace_with_tmp(video_path, lambda tmp: _strip_audio(video_path, tmp))

    last_frame = extract_last_frame(
        video_path, frame_dir / f"frame_{uuid.uuid4().hex}.png"
    )
    return str(video_path), last_frame


def mark_conversation_deleted(conv_id: int, title: str = "") -> None:
    """删除会话时把输出目录重命名为 xxx_delete（已存在则依次 +1/+2...），保留文件便于恢复"""
    video_dir, _ = conversation_dirs(conv_id, title)
    folder = video_dir.parent
    if not folder.exists():
        return
    base = f"{folder.name}_delete"
    dest = folder.parent / base
    n = 1
    while dest.exists():
        dest = folder.parent / f"{base}{n}"
        n += 1
    folder.rename(dest)