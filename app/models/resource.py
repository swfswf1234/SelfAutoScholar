from sqlalchemy import Column, String, Text, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base
import uuid


def uuid_str():
    return str(uuid.uuid4())


class Resource(Base):
    __tablename__ = "resources"

    id = Column(String, primary_key=True, default=uuid_str)
    resource_type = Column(String(20), nullable=False, index=True)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    description = Column(Text)
    course_tags = Column(JSONB, default=list)
    author = Column(String(200))
    platform = Column(String(100))
    is_favorite = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
