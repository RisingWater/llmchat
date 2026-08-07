"""视频生成与展示（图生视频会话）"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import Conversation, GeneratedVideo
from backend.video_service import VIDEO_DIR

router = APIRouter(prefix="/api/videos", tags=["videos"])


class VideoGenerateRequest(BaseModel):
    conversation_id: int
    prompt: str


class VideoGenerateResponse(BaseModel):
    video_url: str
    prompt: str


@router.get("/{video_id}")
def serve_video(video_id: int, db: Session = Depends(get_db)):
    """返回视频文件"""
    video = db.query(GeneratedVideo).get(video_id)
    if not video:
        raise HTTPException(404, "视频不存在")
    path = VIDEO_DIR / video.filename
    if not path.exists():
        raise HTTPException(404, "视频文件不存在")
    return FileResponse(str(path), media_type="video/mp4")


@router.post("/generate", response_model=VideoGenerateResponse)
async def generate_video(
    body: VideoGenerateRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """生成一段视频（图生视频）

    当前为占位实现：返回 501。后续流程：
      1. 取会话首帧/上一轮视频的最后一帧作为输入图
      2. ComfyUI 生成视频 → 存 output/videos/
      3. 截取新视频最后一帧，存为下一轮输入
      4. 与上一个视频合并（ffmpeg concat），更新会话 merged_video_path
      5. 生成 assistant 消息（content 含 <video> 标签）返回给前端
    """
    conv = db.query(Conversation).get(body.conversation_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    if conv.conv_type != "video":
        raise HTTPException(400, "该会话不是图生视频会话")
    raise HTTPException(501, "视频生成功能尚未实现")
