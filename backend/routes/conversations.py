from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.config import MODEL_PROFILES
from backend.database import get_db
from backend.models import Conversation, Message, GeneratedImage
from backend.schemas import (
    ConversationCreate,
    ConversationDetail,
    ConversationOut,
    ConversationUpdate,
    ForkRequest,
)
from backend.video_service import mark_conversation_deleted

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return (
        db.query(Conversation)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


@router.post("", response_model=ConversationOut)
def create_conversation(
    body: ConversationCreate = ConversationCreate(),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    conv = Conversation(
        title=body.title,
        system_prompt=body.system_prompt,
        model=body.model if body.model in MODEL_PROFILES else "deepseek",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.post("/video", response_model=ConversationOut)
async def create_video_conversation(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """创建图生视频会话：上传第一张图片作为起始画面

    无默认 system_prompt；首图存入 generated_images，作为会话第一条 user 消息
    """
    data = await file.read()
    if not data:
        raise HTTPException(400, "请上传第一张图片")

    conv = Conversation(
        title=title or "图生视频",
        conv_type="video",
        system_prompt="",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    # 首图作为第一条 user 消息（先建消息拿到 id，再关联图片）
    msg = Message(conversation_id=conv.id, role="user", content="")
    db.add(msg)
    db.commit()
    db.refresh(msg)

    img = GeneratedImage(message_id=msg.id, prompt="起始画面", data=data)
    db.add(img)
    db.commit()
    db.refresh(img)

    msg.content = f"![起始画面](/api/images/{img.id})"
    db.commit()

    return conv


@router.get("/{conv_id}", response_model=ConversationDetail)
def get_conversation(conv_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    conv = db.query(Conversation).get(conv_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    return conv


@router.put("/{conv_id}", response_model=ConversationOut)
def update_conversation(
    conv_id: int,
    body: ConversationUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    conv = db.query(Conversation).get(conv_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    if body.title is not None:
        conv.title = body.title
    if body.system_prompt is not None:
        conv.system_prompt = body.system_prompt
    if body.model is not None:
        if body.model not in MODEL_PROFILES:
            raise HTTPException(400, "未知模型")
        conv.model = body.model
    if body.megapixels is not None:
        conv.megapixels = body.megapixels
    if body.steps is not None:
        conv.steps = body.steps
    if body.duration is not None:
        conv.duration = body.duration
    if body.keep_audio is not None:
        conv.keep_audio = int(body.keep_audio)
    db.commit()
    db.refresh(conv)
    return conv


class ClearMessagesResponse(BaseModel):
    ok: bool


@router.delete("/{conv_id}/messages", response_model=ClearMessagesResponse)
def clear_conversation_messages(
    conv_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """清除指定会话的所有消息，保留会话和 system prompt"""
    conv = db.query(Conversation).get(conv_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    db.query(Message).filter(Message.conversation_id == conv_id).delete()
    db.commit()
    return {"ok": True}


@router.delete("/{conv_id}")
def delete_conversation(conv_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    conv = db.query(Conversation).get(conv_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    # 输出目录改名为 xxx_delete（存在则 +1/+2...），保留文件便于恢复
    mark_conversation_deleted(conv.id, conv.title)
    db.delete(conv)
    db.commit()
    return {"ok": True}


@router.post("/{conv_id}/fork", response_model=ConversationOut)
def fork_conversation(
    conv_id: int,
    body: ForkRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """从某条消息处分叉出新的会话

    新会话复制原会话中该消息（含）之前的全部消息与 system prompt，
    之后两边互不影响；原会话保持不动。
    """
    conv = db.query(Conversation).get(conv_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    if conv.conv_type == "video":
        raise HTTPException(400, "图生视频会话不支持分叉")

    src_msg = (
        db.query(Message)
        .filter(Message.id == body.message_id, Message.conversation_id == conv_id)
        .first()
    )
    if not src_msg:
        raise HTTPException(404, "消息不存在")

    title = conv.title or "会话"
    if len(title) > 190:
        title = title[:190]

    fork = Conversation(
        title=f"{title} · 分叉",
        conv_type="chat",
        system_prompt=conv.system_prompt,
        model=conv.model,
        parent_conversation_id=conv.id,
        fork_from_message_id=src_msg.id,
    )
    db.add(fork)
    db.flush()

    history = (
        db.query(Message)
        .filter(Message.conversation_id == conv_id, Message.id <= src_msg.id)
        .order_by(Message.id)
        .all()
    )
    for m in history:
        db.add(Message(
            conversation_id=fork.id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
        ))

    db.commit()
    db.refresh(fork)
    return fork
