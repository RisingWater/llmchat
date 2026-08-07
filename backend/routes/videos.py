"""视频生成与展示（图生视频会话）"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import Conversation, Message, GeneratedImage, GeneratedVideo
from backend.video_service import (
    FRAME_DIR,
    VIDEO_DIR,
    ensure_dirs,
    generate_video_file,
    merge_videos,
)

router = APIRouter(prefix="/api/videos", tags=["videos"])


class VideoGenerateRequest(BaseModel):
    conversation_id: int
    prompt: str


class VideoGenerateResponse(BaseModel):
    video_url: str
    prompt: str


def _first_frame_to_file(conv_id: int, db: Session) -> str:
    """取会话首帧（上传图中数据库 BLOB）落盘为临时输入帧，返回文件路径"""
    first = (
        db.query(GeneratedImage)
        .join(Message, Message.id == GeneratedImage.message_id)
        .filter(Message.conversation_id == conv_id)
        .order_by(Message.id, GeneratedImage.id)
        .first()
    )
    if not first:
        raise HTTPException(404, "会话没有起始画面")
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    path = FRAME_DIR / f"input_{uuid.uuid4().hex}.png"
    path.write_bytes(first.data)
    return str(path)


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

    流程：
      1. 取输入帧：上一轮视频的最后一帧（conv.last_frame_path），否则取会话首图
      2. 保存用户提示词消息，并立即写 assistant 消息"正在生成…"（中间重开页面也可见）
      3. ComfyUI 生成视频 → 存 output/videos/
      4. 截取新视频最后一帧，作为下一轮输入（更新 conv.last_frame_path），与上一轮合并
      5. 建 GeneratedVideo 记录，并把"正在生成"消息替换为 <video> 标签
    """
    conv = db.query(Conversation).get(body.conversation_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    if conv.conv_type != "video":
        raise HTTPException(400, "该会话不是图生视频会话")

    ensure_dirs()

    # 1. 输入帧：上一轮最后一帧，否则首帧
    input_frame = conv.last_frame_path
    if not input_frame:
        input_frame = _first_frame_to_file(conv.id, db)
    if not Path(input_frame).exists():
        raise HTTPException(400, "起始画面文件不存在")

    # 2. 保存用户提示词消息 + 回复"已开始生成"（生成中重新打开页面也能看到）
    user_msg = Message(conversation_id=conv.id, role="user", content=body.prompt)
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content="正在生成视频，请稍候...",
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    # 3. 生成视频（内部含截取最后一帧）
    try:
        video_path, last_frame = await generate_video_file(
            body.prompt,
            input_frame,
            megapixels=conv.megapixels,
            steps=conv.steps,
        )
    except Exception as e:
        assistant_msg.content = f"❌ 视频生成失败: {e}"
        db.commit()
        raise HTTPException(500, f"视频生成失败: {e}")

    # 4. 更新会话状态并合并到完整视频
    conv.last_frame_path = last_frame
    if conv.merged_video_path and Path(conv.merged_video_path).exists():
        merged = str(VIDEO_DIR / f"merged_{uuid.uuid4().hex}.mp4")
        conv.merged_video_path = merge_videos([conv.merged_video_path, video_path], merged)
    else:
        conv.merged_video_path = video_path
    db.commit()

    # 5. 视频记录 + 把"生成中"消息内容替换为视频标签
    gen_video = GeneratedVideo(
        conversation_id=conv.id,
        message_id=assistant_msg.id,
        prompt=body.prompt,
        filename=Path(video_path).name,
    )
    db.add(gen_video)
    db.commit()
    db.refresh(gen_video)

    assistant_msg.content = f'<video src="/api/videos/{gen_video.id}"></video>'
    db.commit()

    return VideoGenerateResponse(video_url=f"/api/videos/{gen_video.id}", prompt=body.prompt)
