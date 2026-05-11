"""数据库连接 — 连接池 + Session 管理"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

from app.core.config import settings

engine = create_engine(
    settings.db_url,
    echo=False,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_conn():
    return SessionLocal()


def init_tables():
    """创建所有表 (幂等: IF NOT EXISTS)"""
    from sqlalchemy import inspect
    from app.models import Base as ModelsBase
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    tables = [t for t in ModelsBase.metadata.tables.values() if t.name not in existing]
    if tables:
        ModelsBase.metadata.create_all(bind=engine, tables=tables)
        return len(tables)
    return 0


def check_db() -> bool:
    """测试数据库连通性"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
