"""User ORM 模型"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    email = Column(String(100), comment="邮箱")
    interest_profile = Column(JSONB, default=dict, comment="兴趣画像: {keywords, categories, weights}")
    preferences = Column(JSONB, default=dict, comment="其他偏好设置")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<User(username={self.username})>"