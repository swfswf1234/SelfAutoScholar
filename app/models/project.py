"""Project ORM 模型 - GitHub 项目表"""

import uuid
from datetime import date, datetime

from sqlalchemy import Column, String, Text, Boolean, Integer, Date, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class Project(Base):
    """GitHub 项目表"""

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_id = Column(String(200), unique=True, comment="owner/repo 格式")
    name = Column(String(200), nullable=False, comment="项目名称")
    full_name = Column(String(400), comment="完整名称 (owner/name)")
    description = Column(Text, comment="项目描述")
    description_cn = Column(Text, comment="中文描述")
    readme_content = Column(Text, comment="README 原始内容")
    readme_summary = Column(Text, comment="AI 总结")
    source_url = Column(Text, comment="GitHub 地址")
    local_readme_path = Column(Text, comment="本地 README 路径")

    # 项目元数据
    stars = Column(Integer, default=0, comment="Star 数")
    forks = Column(Integer, default=0, comment="Fork 数")
    language = Column(String(50), comment="主要编程语言")
    topics = Column(JSONB, default=list, comment="项目主题标签")
    license = Column(String(100), comment="开源协议")

    # 评估结果
    is_important = Column(Boolean, comment="重要性: true=重要, false=不重要")
    is_relevant = Column(Boolean, comment="相关性: true=相关, false=不相关")
    is_interested = Column(Boolean, comment="兴趣: true=感兴趣, false=不感兴趣")
    is_downloaded = Column(Boolean, default=False, comment="是否已下载")
    is_read = Column(Boolean, default=False, comment="是否已读")

    # 用户标签
    user_tags = Column(JSONB, default=list, comment="用户自定义标签")

    # 时间信息
    pushed_at = Column(DateTime, comment="最后推送时间")
    processed_date = Column(Date, default=date.today, comment="处理日期")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Project(name={self.name}, stars={self.stars})>"