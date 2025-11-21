"""
Database models for voice sessions and state persistence
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Integer,
    ForeignKey,
    Text,
    JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


def generate_uuid():
    """Generate UUID string"""
    return str(uuid.uuid4())


class VoiceSession(Base):
    """Voice session model"""
    __tablename__ = "voice_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    transcripts = relationship(
        "TranscriptChunk",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    snapshots = relationship(
        "SessionSnapshot",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionSnapshot.created_at.desc()"
    )

    def __repr__(self):
        return f"<VoiceSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"


class TranscriptChunk(Base):
    """Transcript chunk model"""
    __tablename__ = "transcript_chunks"

    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("voice_sessions.id"), nullable=False, index=True)
    speaker = Column(String, nullable=False)  # 'user' or 'agent'
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    metadata = Column(JSON, default=dict)

    # Relationships
    session = relationship("VoiceSession", back_populates="transcripts")

    def __repr__(self):
        return f"<TranscriptChunk(id={self.id}, speaker={self.speaker}, deleted={self.is_deleted})>"


class SessionSnapshot(Base):
    """
    Session state snapshot for recovery

    Periodic snapshots of session state stored in Postgres
    for restoration after disconnects or crashes
    """
    __tablename__ = "session_snapshots"

    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("voice_sessions.id"), nullable=False, index=True)
    agent_state = Column(String, nullable=False)  # idle/listening/thinking/speaking
    transcript_count = Column(Integer, default=0, nullable=False)
    metadata = Column(JSON, default=dict)
    device_ids = Column(JSON, default=list)  # List of connected device IDs
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    session = relationship("VoiceSession", back_populates="snapshots")

    def __repr__(self):
        return f"<SessionSnapshot(id={self.id}, session_id={self.session_id}, state={self.agent_state})>"
