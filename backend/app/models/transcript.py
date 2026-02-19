from sqlalchemy import Column, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..database import Base

class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"))
    raw_text = Column(Text, nullable=False)
    reconstructed_text = Column(Text, nullable=True)

    meeting = relationship("Meeting", back_populates="transcripts")
