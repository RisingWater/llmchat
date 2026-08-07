from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship

from backend.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), default="New Chat")
    system_prompt = Column(Text, default="You are a helpful assistant.")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    messages = relationship("Message", back_populates="conversation",
                            order_by="Message.id", cascade="all, delete-orphan")


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


class GeneratedImage(Base):
    __tablename__ = "generated_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    prompt = Column(Text, default="")
    data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    message = relationship("Message", back_populates="generated_images")
