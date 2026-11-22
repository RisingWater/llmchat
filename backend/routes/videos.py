"""视频生成与展示（图生视频会话）"""
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.llm_client import stream_chat
from backend.models import Conversation, Message, GeneratedImage, GeneratedVideo
from backend.video_service import (
    append_merged,
    conversation_dirs,
    ensure_dirs,
    extract_last_frame,
    generate_video_file,
    rebuild_merged,
)
from backend.wechat_notify import notify_video_done

router = APIRouter(prefix="/api/videos", tags=["videos"])


class VideoGenerateRequest(BaseModel):
    conversation_id: int
    prompt: str


class VideoGenerateResponse(BaseModel):
    video_url: str
    prompt: str


class PolishRequest(BaseModel):
    conversation_id: int
    prompt: str


class PolishResponse(BaseModel):
    prompt: str


POLISH_INSTRUCTION = (
    "你是一名专业的 AI 视频提示词润色师。用户会给你一段用于 MiniMax H3 图生视频的中文提示词，"
    "请将其润色为更详细、更适合视频生成的中文提示词：补充动作、镜头运动、光线、氛围等细节，"
    "保持人物/场景与首帧画面一致。只输出润色后的提示词本身，"
    "不要任何解释、引号、标点外多余文字或代码块。输出必须使用中文，控制在 200 字以内。"
)


class UndoRequest(BaseModel):
    conversation_id: int


class UndoResponse(BaseModel):
    ok: bool


def _first_frame_to_file(conv: Conversation, db: Session) -> str:
    """取会话首帧（上传图中数据库 BLOB）落盘到会话的帧目录，返回文件路径"""
    first = (
        db.query(GeneratedImage)
        .join(Message, Message.id == GeneratedImage.message_id)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.id, GeneratedImage.id)
        .first()
    )
    if not first:
        raise HTTPException(404, "会话没有起始画面")
    _, frame_dir = conversation_dirs(conv.id, conv.title)
    frame_dir.mkdir(parents=True, exist_ok=True)
    path = frame_dir / f"input_{uuid.uuid4().hex}.png"
    path.write_bytes(first.data)
    return str(path)


@router.get("/{video_id}")
def serve_video(video_id: int, db: Session = Depends(get_db)):
    """返回视频文件"""
    video = db.query(GeneratedVideo).get(video_id)
    if not video:
        raise HTTPException(404, "视频不存在")
    video_dir, _ = conversation_dirs(
        video.conversation_id,
        video.conversation.title if video.conversation else "",
    )
    path = video_dir / video.filename
    if not path.exists():
        raise HTTPException(404, "视频文件不存在")
    return FileResponse(str(path), media_type="video/mp4")


@router.get("/merged/{conv_id}")
def serve_merged(conv_id: int, db: Session = Depends(get_db)):
    """返回会话最终成片（所有片段拼成的 merged.mp4）"""
    conv = db.query(Conversation).get(conv_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    if not conv.merged_video_path or not Path(conv.merged_video_path).exists():
        raise HTTPException(404, "还没有成片")
    return FileResponse(conv.merged_video_path, media_type="video/mp4")


@router.post("/undo", response_model=UndoResponse)
def undo_step(
    body: UndoRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """回到上一步：删除最新片段、其提示词消息与视频记录，用前一个 frame 继续生成，并重新拼接成片"""
    conv = db.query(Conversation).get(body.conversation_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    if conv.conv_type != "video":
        raise HTTPException(400, "该会话不是图生视频会话")

    video_dir, frame_dir = conversation_dirs(conv.id, conv.title)

    last = (
        db.query(GeneratedVideo)
        .filter(GeneratedVideo.conversation_id == conv.id)
        .order_by(GeneratedVideo.id.desc())
        .first()
    )
    if not last:
        raise HTTPException(400, "没有可回退的步骤")

    # 删除最新片段文件
    (video_dir / last.filename).unlink(missing_ok=True)
    # 删除该片段的 assistant 消息与记录
    db.query(Message).filter(Message.id == last.message_id).delete()
    db.delete(last)
    # 删除该轮提示词（最新一条 user 消息）
    latest_user = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id, Message.role == "user")
        .order_by(Message.id.desc())
        .first()
    )
    if latest_user:
        db.delete(latest_user)
    db.commit()

    # 用剩余最后一个片段的最后一帧作为下一轮输入，并重新拼接成片
    remaining = (
        db.query(GeneratedVideo)
        .filter(GeneratedVideo.conversation_id == conv.id)
        .order_by(GeneratedVideo.id)
        .all()
    )
    if remaining:
        prev_seg = video_dir / remaining[-1].filename
        conv.last_frame_path = extract_last_frame(
            prev_seg, frame_dir / f"frame_{uuid.uuid4().hex}.png"
        )
        conv.merged_video_path = rebuild_merged(
            [video_dir / v.filename for v in remaining], video_dir
        )
    else:
        conv.last_frame_path = None
        conv.merged_video_path = rebuild_merged([], video_dir)
    db.commit()
    return UndoResponse(ok=True)


@router.post("/polish", response_model=PolishResponse)
async def polish_prompt(
    body: PolishRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """用 DeepSeek 润色视频提示词（中文），可反复调用直至满意"""
    conv = db.query(Conversation).get(body.conversation_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    if conv.conv_type != "video":
        raise HTTPException(400, "该会话不是图生视频会话")

    messages = [
        {"role": "system", "content": POLISH_INSTRUCTION},
        {"role": "user", "content": body.prompt},
    ]
    parts: list[str] = []
    try:
        async for event in stream_chat(messages, conv.model):
            if event["type"] == "content":
                parts.append(event["content"])
    except Exception as e:
        raise HTTPException(500, f"提示词润色失败: {e}")

    polished = "".join(parts).strip().strip('"\'`')
    if not polished:
        raise HTTPException(500, "润色未返回结果")
    return PolishResponse(prompt=polished)


@router.post("/generate", response_model=VideoGenerateResponse)
async def generate_video(
    body: VideoGenerateRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    tasks: BackgroundTasks = BackgroundTasks(),
):
    """生成一段视频（图生视频）

    流程：
      1. 取输入帧：上一轮视频的最后一帧（conv.last_frame_path），否则取会话首图
      2. 保存用户提示词消息，并立即写 assistant 消息"正在生成…"（中间重开页面也可见）
      3. ComfyUI 生成视频 → 存会话目录 output/{id}_{标题}/videos/
      4. 截取新视频最后一帧到会话帧目录，作为下一轮输入（更新 conv.last_frame_path），与上一轮合并
      5. 建 GeneratedVideo 记录，并把"正在生成"消息替换为 <video> 标签
    """
    conv = db.query(Conversation).get(body.conversation_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    if conv.conv_type != "video":
        raise HTTPException(400, "该会话不是图生视频会话")

    ensure_dirs(conv.id, conv.title)
    video_dir, frame_dir = conversation_dirs(conv.id, conv.title)

    # 1. 输入帧：上一轮最后一帧，否则首帧
    input_frame = conv.last_frame_path
    if not input_frame:
        input_frame = _first_frame_to_file(conv, db)
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
            duration=conv.duration,
            video_dir=video_dir,
            frame_dir=frame_dir,
            keep_audio=bool(conv.keep_audio),
        )
    except Exception as e:
        assistant_msg.content = f"❌ 视频生成失败: {e}"
        db.commit()
        raise HTTPException(500, f"视频生成失败: {e}")

    # 4. 更新会话状态并拼到成片（只保留一份 merged.mp4）
    conv.last_frame_path = last_frame
    if conv.merged_video_path and Path(conv.merged_video_path).exists():
        conv.merged_video_path = append_merged(conv.merged_video_path, video_path, video_dir)
    else:
        conv.merged_video_path = rebuild_merged([video_path], video_dir)
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

    # 6. 视频完成，后台发微信通知（不阻塞响应）
    tasks.add_task(notify_video_done, conv.title)

    return VideoGenerateResponse(video_url=f"/api/videos/{gen_video.id}", prompt=body.prompt)
