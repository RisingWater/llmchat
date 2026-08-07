"""图片生成与存储 — 全部存入数据库，不留本地文件"""
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.image_gen import generate_image
from backend.llm_client import stream_chat
from backend.models import Conversation, Message, GeneratedImage

router = APIRouter(prefix="/api/images", tags=["images"])


class GenerateRequest(BaseModel):
    conversation_id: int
    message_id: int


class GenerateResponse(BaseModel):
    image_url: str
    prompt: str


PROMPT_INSTRUCTION = (
    "根据上面的对话，想象你是这个聊天中的角色。"
    "描述你当前的外貌、衣着、表情、所处的环境、正在做的事情。"
    "只输出一段用于AI图片生成的详细中文提示词，不要输出其他内容。"
    "注重画面细节：画风（二次元/写实/数字艺术）、光线、构图、色彩、氛围。200字以内。"
    "不要提到'AI助手'或'assistant'，你就是对话中的那个角色。"
)


@router.get("/{image_id}")
def serve_image(image_id: int, db: Session = Depends(get_db)):
    """从数据库读取图片并返回"""
    img = db.query(GeneratedImage).get(image_id)
    if not img:
        raise HTTPException(404, "图片不存在")
    return Response(content=img.data, media_type="image/png")


@router.post("/generate", response_model=GenerateResponse)
async def generate_conversation_image(
    body: GenerateRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    conv = db.query(Conversation).get(body.conversation_id)
    if not conv:
        raise HTTPException(404, "会话不存在")

    target_msg = db.query(Message).get(body.message_id)
    if not target_msg:
        raise HTTPException(404, "消息不存在")

    # 构建上下文
    messages = [{"role": "system", "content": conv.system_prompt}]
    history = (
        db.query(Message)
        .filter(
            Message.conversation_id == body.conversation_id,
            Message.id <= body.message_id,
        )
        .order_by(Message.id)
        .all()
    )
    for m in history:
        messages.append({"role": m.role, "content": m.content})

    messages.append({"role": "user", "content": PROMPT_INSTRUCTION})

    # LLM 生成提示词
    prompt_parts: list[str] = []
    try:
        async for event in stream_chat(messages):
            if event["type"] == "content":
                prompt_parts.append(event["content"])
    except Exception as e:
        raise HTTPException(500, f"LLM 调用失败: {e}")

    raw_prompt = "".join(prompt_parts).strip()
    raw_prompt = re.sub(r"^['\"]+|['\"]+$", "", raw_prompt)
    raw_prompt = raw_prompt.replace("```", "").strip()

    if not raw_prompt:
        raise HTTPException(500, "LLM 未返回有效提示词")

    # 生成图片
    img_data = await generate_image(raw_prompt)
    if not img_data:
        raise HTTPException(500, "图片生成失败")

    # 存入数据库
    gen_img = GeneratedImage(
        message_id=body.message_id,
        prompt=raw_prompt,
        data=img_data,
    )
    db.add(gen_img)
    db.commit()
    db.refresh(gen_img)

    url = f"/api/images/{gen_img.id}"

    # 同时追加到消息 content 中，保证刷新后可见
    img_md = f"\n\n![{raw_prompt[:50]}]({url})"
    target_msg.content = (target_msg.content or "") + img_md
    db.commit()

    return GenerateResponse(image_url=url, prompt=raw_prompt)
