"""News ORM 模型 - 新闻表"""

import uuid
from datetime import date, datetime

from sqlalchemy import Column, String, Text, Boolean, Date, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class News(Base):
    """新闻表"""

    __tablename__ = "news"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False, comment="新闻标题")
    title_cn = Column(Text, comment="中文标题")
    summary = Column(Text, comment="AI 摘要")

    # 来源信息
    source_name = Column(String(100), comment="来源网站名称")
    source_url = Column(Text, comment="原始链接")
    author = Column(String(200), comment="作者")
    local_path = Column(Text, comment="本地保存路径")

    # 评估结果
    is_important = Column(Boolean, comment="重要性: true=重要, false=不重要")
    is_relevant = Column(Boolean, comment="相关性: true=相关, false=不相关")
    is_interested = Column(Boolean, comment="兴趣: true=感兴趣, false=不感兴趣")
    is_downloaded = Column(Boolean, default=False, comment="是否已下载")
    is_read = Column(Boolean, default=False, comment="是否已读")

    # 用户标签
    user_tags = Column(JSONB, default=list, comment="用户自定义标签")

    # 时间信息
    published_at = Column(DateTime, comment="发布时间")
    processed_date = Column(Date, default=date.today, comment="处理日期")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<News(title={self.title[:30]}...)>"