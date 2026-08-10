from datetime import datetime
from pydantic import BaseModel, Field


# ---- Login ----
class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str


# ---- Conversation ----
class ConversationCreate(BaseModel):
    title: str = "New Chat"
    system_prompt: str = "You are a helpful assistant."


class ConversationUpdate(BaseModel):
    title: str | None = None
    system_prompt: str | None = None
    megapixels: float | None = None
    steps: int | None = None
    duration: int | None = None
    keep_audio: bool | None = None


class ConversationOut(BaseModel):
    id: int
    title: str
    conv_type: str
    system_prompt: str
    megapixels: float = 0.8
    steps: int = 8
    duration: int = 5
    keep_audio: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationOut):
    messages: list["MessageOut"]


# ---- Message ----
class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    content: str
