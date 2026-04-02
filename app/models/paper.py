"""Paper ORM 模型"""

import uuid
from datetime import date, datetime

from sqlalchemy import Column, String, Text, Boolean, Date, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class Paper(Base):
    """论文表"""

    __tablename__ = "papers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    arxiv_id = Column(String(50), unique=True, comment="arXiv ID")
    title = Column(Text, nullable=False, comment="论文标题")
    abstract = Column(Text, comment="摘要")
    authors = Column(JSONB, default=list, comment="作者列表")
    keywords = Column(JSONB, default=list, comment="关键词")
    categories = Column(JSONB, default=list, comment="arXiv 分类")
    source_url = Column(Text, comment="论文来源地址")
    pdf_url = Column(Text, comment="PDF 下载地址")
    local_path = Column(Text, comment="本地保存路径")

    # 评估结果
    is_important = Column(Boolean, comment="重要性: true=重要, false=不重要")
    is_relevant = Column(Boolean, comment="相关性: true=相关, false=不相关")
    is_interested = Column(Boolean, comment="兴趣: true=感兴趣, false=不感兴趣")
    is_downloaded = Column(Boolean, default=False, comment="是否已下载")

    # 时间信息
    published_date = Column(Date, comment="论文发布日期")
    processed_date = Column(Date, default=date.today, comment="处理日期")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Paper(arxiv_id={self.arxiv_id}, title={self.title[:30]}...)>"
