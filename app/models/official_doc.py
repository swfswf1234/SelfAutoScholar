from sqlalchemy import Column, String, Text, Integer, DateTime, func
from app.core.database import Base
import uuid


def uuid_str():
    return str(uuid.uuid4())


class OfficialDoc(Base):
    __tablename__ = "official_docs"

    id = Column(String, primary_key=True, default=uuid_str)
    name = Column(String(100), nullable=False, index=True)
    version = Column(String(50))
    source_url = Column(Text)
    local_path = Column(Text)
    pages_count = Column(Integer, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
