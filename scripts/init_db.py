"""数据库初始化 — 创建 qed_tracker 数据库 + 4 张表

用法:
    python scripts/init_db.py          # 创建表 (数据库需已存在)
    python scripts/init_db.py --create-db   # 尝试创建数据库
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from loguru import logger

from app.core.config import settings
from app.core.database import engine, init_tables, check_db


def create_database():
    """尝试创建 qed_tracker 数据库"""
    base_url = f"postgresql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/postgres"
    try:
        eng = create_engine(base_url, isolation_level="AUTOCOMMIT")
        with eng.connect() as conn:
            exists = conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{settings.db_name}'")
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{settings.db_name}" ENCODING "UTF8"'))
                logger.info(f"数据库 '{settings.db_name}' 已创建")
            else:
                logger.info(f"数据库 '{settings.db_name}' 已存在")
        eng.dispose()
    except Exception as e:
        logger.error(f"创建数据库失败: {e}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="QED-Tracker 数据库初始化")
    parser.add_argument("--create-db", action="store_true", help="创建数据库（如不存在）")
    args = parser.parse_args()

    if args.create_db:
        print("创建数据库...")
        if not create_database():
            sys.exit(1)

    print("连接数据库...")
    if not check_db():
        print(f"[失败] 无法连接: {settings.db_url}")
        print(f"  请确认 PostgreSQL 已启动, 且数据库 '{settings.db_name}' 已存在")
        print(f"  或使用 --create-db 参数自动创建")
        sys.exit(1)

    print("创建表结构...")
    created = init_tables()
    if created:
        print(f"✓ 已创建 {created} 张表")
    else:
        print("✓ 表已存在，无需创建")

    print("\n初始化完成")


if __name__ == "__main__":
    main()
