import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db, SessionLocal
from backend.llm_client import stream_chat
from backend.models import Conversation, Message
from backend.schemas import ChatRequest

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/{conv_id}")
async def chat(
    conv_id: int,
    body: ChatRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    conv = db.query(Conversation).get(conv_id)
    if not conv:
        raise HTTPException(404, "会话不存在")

    # 保存用户消息
    user_msg = Message(conversation_id=conv_id, role="user", content=body.content)
    db.add(user_msg)

    msg_count = db.query(Message).filter(Message.conversation_id == conv_id).count()
    if msg_count == 1 and conv.title in ("New Chat", "新的聊天"):
        conv.title = body.content[:30]

    db.commit()

    # 构建消息
    history = (
        db.query(Message)
        .filter(Message.conversation_id == conv_id)
        .order_by(Message.id)
        .all()
    )
    api_messages = [{"role": "system", "content": conv.system_prompt}]
    for m in history:
        api_messages.append({"role": m.role, "content": m.content})

    # SSE 流式返回
    async def generate():
        full_text: list[str] = []

        try:
            async for event in stream_chat(api_messages):
                if event["type"] == "content":
                    full_text.append(event["content"])
                    yield f"data: {json.dumps({'content': event['content']})}\n\n"
                elif event["type"] == "error":
                    yield f"data: {json.dumps({'error': event['message']})}\n\n"
                    yield "data: [DONE]\n\n"
                    return
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"
            return

        yield "data: [DONE]\n\n"

        # 保存
        save_content = "".join(full_text).strip()
        if save_content:
            save_db = SessionLocal()
            try:
                assistant_msg = Message(
                    conversation_id=conv_id,
                    role="assistant",
                    content=save_content,
                )
                save_db.add(assistant_msg)
                save_db.commit()
            finally:
                save_db.close()

    return StreamingResponse(generate(), media_type="text/event-stream")
