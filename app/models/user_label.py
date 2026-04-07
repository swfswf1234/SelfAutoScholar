"""UserLabel ORM 模型 - 用户打标记录表"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, func, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class UserLabel(Base):
    """用户打标记录表"""

    __tablename__ = "user_labels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="用户 ID")
    item_type = Column(String(20), nullable=False, comment="类型: paper/project/news")
    item_id = Column(UUID(as_uuid=True), nullable=False, comment="项目 ID")
    label = Column(String(20), nullable=False, comment="标签: interested/not_interested/read/starred")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    __table_args__ = (
        UniqueConstraint("user_id", "item_type", "item_id", "label", name="uq_user_label"),
    )

    def __repr__(self):
        return f"<UserLabel(user_id={self.user_id}, label={self.label})>"