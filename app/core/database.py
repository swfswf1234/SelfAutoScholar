"""数据库连接模块"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.db_url,
    echo=False,  # 设为 True 可打印 SQL 日志
    pool_pre_ping=True,
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()


def get_db():
    """获取数据库会话 (依赖注入用)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库 (创建所有表)"""
    Base.metadata.create_all(bind=engine)
