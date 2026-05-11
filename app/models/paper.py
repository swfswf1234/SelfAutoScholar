from sqlalchemy import Column, String, Text, Date, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base
import uuid


def uuid_str():
    return str(uuid.uuid4())


class Paper(Base):
    __tablename__ = "papers"

    id = Column(String, primary_key=True, default=uuid_str)
    arxiv_id = Column(String(50), unique=True, nullable=False)
    title = Column(Text, nullable=False)
    title_cn = Column(Text)
    authors = Column(JSONB, default=list)
    categories = Column(JSONB, default=list)
    published_date = Column(Date)
    source_url = Column(Text)
    local_path = Column(Text)
    course_tags = Column(JSONB, default=list)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
