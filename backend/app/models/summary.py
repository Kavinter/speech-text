from sqlalchemy import Column, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..database import Base

class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"))
    executive_summary = Column(Text, nullable=True)
    topics_json = Column(Text, nullable=True)
    decisions_json = Column(Text, nullable=True)
    action_items_json = Column(Text, nullable=True)
    discussions_json = Column(Text, nullable=True)

    meeting = relationship("Meeting", back_populates="summaries")
