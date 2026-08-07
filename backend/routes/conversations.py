from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import Conversation, Message, GeneratedImage
from backend.schemas import (
    ConversationCreate,
    ConversationDetail,
    ConversationOut,
    ConversationUpdate,
)

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
    conv = Conversation(title=body.title, system_prompt=body.system_prompt)
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
    if body.megapixels is not None:
        conv.megapixels = body.megapixels
    if body.steps is not None:
        conv.steps = body.steps
    if body.duration is not None:
        conv.duration = body.duration
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
    db.delete(conv)
    db.commit()
    return {"ok": True}
