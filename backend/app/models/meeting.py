from sqlalchemy import Column, Integer, String, DateTime, Enum, Float
from ..database import Base
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
import enum

class MeetingStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    date = Column(DateTime, nullable=False)
    audio_file_path = Column(String(255), nullable=False)
    duration = Column(Float, nullable=True)
    status = Column(Enum(MeetingStatus), default=MeetingStatus.pending, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    transcripts = relationship("Transcript", back_populates="meeting", cascade="all, delete-orphan")
    summaries = relationship("Summary", back_populates="meeting", cascade="all, delete-orphan")
    speakers = relationship("Speaker", back_populates="meeting", cascade="all, delete-orphan")