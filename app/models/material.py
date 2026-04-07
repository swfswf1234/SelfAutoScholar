"""Material ORM 模型 - 资料汇总表"""

import uuid
from datetime import date, datetime

from sqlalchemy import Column, String, Text, Boolean, Date, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class Material(Base):
    """资料汇总表"""

    __tablename__ = "materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_type = Column(String(20), nullable=False, comment="类型: paper/project/news")
    item_id = Column(UUID(as_uuid=True), nullable=False, comment="对应表的 ID")
    title = Column(Text, nullable=False, comment="标题")
    summary = Column(Text, comment="摘要")
    source_url = Column(Text, comment="来源链接")

    # 评估结果
    is_important = Column(Boolean, comment="重要性")
    is_relevant = Column(Boolean, comment="相关性")
    is_interested = Column(Boolean, comment="兴趣度")
    is_downloaded = Column(Boolean, default=False, comment="是否已下载")

    # 关联
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), comment="用户 ID")

    # 时间信息
    processed_date = Column(Date, default=date.today, comment="处理日期")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<Material(item_type={self.item_type}, title={self.title[:30]}...)>"