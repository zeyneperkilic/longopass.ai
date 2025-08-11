from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Enum, ForeignKey, Boolean, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
import datetime
import os

# Allow overriding DB path via environment variable for container persistence
DB_PATH = os.getenv("DB_PATH", "./app.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    plan = Column(String, default="free")  # 'free' or 'premium'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    conversations = relationship("Conversation", back_populates="user")

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="active")  # active/closed
    title = Column(String, nullable=True)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    user_id = Column(Integer, nullable=True)
    role = Column(String)  # system/user/assistant
    content = Column(Text)
    model_name = Column(String, nullable=True)
    model_latency_ms = Column(Integer, nullable=True)
    tokens_in = Column(Integer, nullable=True)
    tokens_out = Column(Integer, nullable=True)
    cost_usd = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
    metas = relationship("MessageMeta", back_populates="message")

class MessageMeta(Base):
    __tablename__ = "message_meta"
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    raw_provider_payload = Column(JSON, nullable=True)
    raw_provider_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    message = relationship("Message", back_populates="metas")
