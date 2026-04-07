#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_database.py - 数据库连接和表结构测试

测试内容:
1. 数据库连接是否正常
2. database.md 要求的 6 张表是否存在
3. 表字段是否完整
4. 默认用户是否存在
5. 基础 CRUD 操作是否可用
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.core.database import engine, SessionLocal, init_db
from app.models import User, Paper, Project, News, Material, UserLabel


class TestDatabaseConnection:
    """数据库连接测试"""

    def test_database_exists(self):
        """测试数据库是否可连接"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
        except OperationalError as e:
            pytest.fail(f"无法连接到数据库: {e}")

    def test_database_name(self):
        """测试当前连接的数据库名"""
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"\n当前数据库: {db_name}")
            assert db_name == settings.db_name, f"期望 {settings.db_name}, 实际 {db_name}"


class TestDatabaseSchema:
    """数据库表结构测试"""

    @classmethod
    def setup_class(cls):
        """初始化数据库表"""
        init_db()

    def test_all_tables_exist(self):
        """测试 6 张表是否都存在"""
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        expected_tables = {"users", "papers", "projects", "news", "materials", "user_labels"}
        
        print(f"\n现有表: {existing_tables}")
        print(f"期望表: {expected_tables}")
        
        missing = expected_tables - existing_tables
        if missing:
            pytest.fail(f"缺少表: {missing}")

    def test_users_table_columns(self):
        """测试 users 表字段"""
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("users")}
        
        expected = {"id", "username", "email", "interest_profile", "preferences", "created_at", "updated_at"}
        missing = expected - columns
        
        if missing:
            print(f"users 表缺少字段: {missing}")
        assert not missing, f"users 表缺少字段: {missing}"

    def test_papers_table_columns(self):
        """测试 papers 表字段"""
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("papers")}
        
        expected = {
            "id", "arxiv_id", "title", "title_cn", "abstract", "abstract_cn",
            "authors", "keywords", "categories", "source_url", "pdf_url", "local_path",
            "summary", "key_points", "is_important", "is_relevant", "is_interested",
            "is_downloaded", "is_read", "user_tags", "published_date", "processed_date",
            "created_at", "updated_at"
        }
        missing = expected - columns
        
        if missing:
            print(f"papers 表缺少字段: {missing}")
        assert not missing, f"papers 表缺少字段: {missing}"

    def test_projects_table_columns(self):
        """测试 projects 表字段"""
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("projects")}
        
        expected = {
            "id", "github_id", "name", "full_name", "description", "description_cn",
            "readme_content", "readme_summary", "source_url", "local_readme_path",
            "stars", "forks", "language", "topics", "license",
            "is_important", "is_relevant", "is_interested", "is_downloaded", "is_read",
            "user_tags", "pushed_at", "processed_date", "created_at", "updated_at"
        }
        missing = expected - columns
        
        if missing:
            print(f"projects 表缺少字段: {missing}")
        assert not missing, f"projects 表缺少字段: {missing}"

    def test_news_table_columns(self):
        """测试 news 表字段"""
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("news")}
        
        expected = {
            "id", "title", "title_cn", "summary", "source_name", "source_url",
            "author", "local_path", "is_important", "is_relevant", "is_interested",
            "is_downloaded", "is_read", "user_tags", "published_at", "processed_date",
            "created_at", "updated_at"
        }
        missing = expected - columns
        
        if missing:
            print(f"news 表缺少字段: {missing}")
        assert not missing, f"news 表缺少字段: {missing}"

    def test_materials_table_columns(self):
        """测试 materials 表字段"""
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("materials")}
        
        expected = {
            "id", "item_type", "item_id", "title", "summary", "source_url",
            "is_important", "is_relevant", "is_interested", "is_downloaded",
            "user_id", "processed_date", "created_at"
        }
        missing = expected - columns
        
        if missing:
            print(f"materials 表缺少字段: {missing}")
        assert not missing, f"materials 表缺少字段: {missing}"

    def test_user_labels_table_columns(self):
        """测试 user_labels 表字段"""
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("user_labels")}
        
        expected = {"id", "user_id", "item_type", "item_id", "label", "created_at"}
        missing = expected - columns
        
        if missing:
            print(f"user_labels 表缺少字段: {missing}")
        assert not missing, f"user_labels 表缺少字段: {missing}"


class TestDefaultUser:
    """默认用户测试"""

    def test_default_user_exists(self):
        """测试默认用户 postgres 是否存在"""
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.username == "postgres").first()
            if user:
                print(f"\n默认用户已存在: {user.username}, email: {user.email}")
            else:
                print("\n默认用户不存在，需要创建")
                # 创建默认用户
                new_user = User(
                    username="postgres",
                    email="postgres@local",
                    interest_profile={},
                    preferences={}
                )
                session.add(new_user)
                session.commit()
                print("已创建默认用户: postgres")
        finally:
            session.close()


class TestCRUDOperations:
    """基础 CRUD 测试"""

    def test_insert_paper(self):
        """测试插入论文"""
        session = SessionLocal()
        try:
            paper = Paper(
                arxiv_id="test.001",
                title="Test Paper",
                abstract="Test abstract",
                authors=["Test Author"],
                categories=["cs.AI"]
            )
            session.add(paper)
            session.commit()
            
            # 查询验证
            result = session.query(Paper).filter(Paper.arxiv_id == "test.001").first()
            assert result is not None
            assert result.title == "Test Paper"
            
            # 清理
            session.delete(result)
            session.commit()
        finally:
            session.close()

    def test_query_users(self):
        """测试查询用户"""
        session = SessionLocal()
        try:
            users = session.query(User).all()
            print(f"\n用户数量: {len(users)}")
            for u in users:
                print(f"  - {u.username}: {u.email}")
        finally:
            session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])