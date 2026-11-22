from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, LargeBinary, Float
from sqlalchemy.orm import relationship

from backend.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), default="New Chat")
    # 会话类型：chat=聊天，video=图生视频
    conv_type = Column(String(20), default="chat")
    system_prompt = Column(Text, default="You are a helpful assistant.")
    # 使用的模型：deepseek / local（档案见 config.MODEL_PROFILES）
    model = Column(String(40), default="deepseek")
    # 单次最大输出（token），会话设置里可调
    max_tokens = Column(Integer, default=10000)
    # 图生视频状态：下一轮输入帧路径、已合并视频路径
    last_frame_path = Column(String(500), nullable=True)
    merged_video_path = Column(String(500), nullable=True)
    # 图生视频生成参数（可在前端设置）
    megapixels = Column(Float, default=0.8)
    steps = Column(Integer, default=8)
    duration = Column(Integer, default=5)
    # 是否保留视频音轨（0=不保留，存盘前去音轨）
    keep_audio = Column(Integer, default=0)
    # 分叉来源：从哪个会话的哪条消息处分叉出来（普通会话为 NULL）
    parent_conversation_id = Column(Integer, nullable=True)
    fork_from_message_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    messages = relationship("Message", back_populates="conversation",
                            order_by="Message.id", cascade="all, delete-orphan")
    videos = relationship("GeneratedVideo", back_populates="conversation",
                          cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="messages")
    generated_images = relationship("GeneratedImage", back_populates="message",
                                    cascade="all, delete-orphan")
    videos = relationship("GeneratedVideo", back_populates="message",
                          cascade="all, delete-orphan")


class GeneratedImage(Base):
    __tablename__ = "generated_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    prompt = Column(Text, default="")
    data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    message = relationship("Message", back_populates="generated_images")


class GeneratedVideo(Base):
    __tablename__ = "generated_videos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    prompt = Column(Text, default="")
    # 视频文件名（相对会话输出目录 output/{id}_{标题}/videos/）
    filename = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="videos")
    message = relationship("Message", back_populates="videos")
