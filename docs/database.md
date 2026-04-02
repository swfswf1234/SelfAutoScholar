# 数据库设计 | Database Schema

## 概述

SelfAutoScholar 使用 PostgreSQL 作为主数据库，存储用户信息、论文、项目、新闻及用户行为数据。

## 表结构

### 1. users — 用户表

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(50) UNIQUE NOT NULL,
    email           VARCHAR(100),
    interest_profile JSONB DEFAULT '{}',          -- 兴趣画像: {"keywords": [...], "categories": [...], "weights": {...}}
    preferences     JSONB DEFAULT '{}',           -- 其他偏好设置
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- 默认用户 (单用户场景)
INSERT INTO users (username, email, interest_profile) 
VALUES ('default', 'default@local', '{}');
```

### 2. papers — 论文表

```sql
CREATE TABLE papers (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    arxiv_id            VARCHAR(50) UNIQUE,           -- arXiv ID (如 2401.12345)
    title               TEXT NOT NULL,                 -- 论文标题
    title_cn            TEXT,                          -- 中文标题 (翻译后)
    abstract            TEXT,                          -- 摘要
    abstract_cn         TEXT,                          -- 中文摘要
    authors             JSONB DEFAULT '[]',            -- 作者列表 ["Author1", "Author2"]
    keywords            JSONB DEFAULT '[]',            -- 关键词
    categories          JSONB DEFAULT '[]',            -- arXiv 分类 ["cs.AI", "cs.CL"]
    source_url          TEXT,                          -- 论文来源地址 (arXiv 页面)
    pdf_url             TEXT,                          -- PDF 下载地址
    local_path          TEXT,                          -- 本地保存路径 (相对于 data/downloads/)
    
    -- AI 分析结果
    summary             TEXT,                          -- AI 生成的总结
    key_points          JSONB DEFAULT '[]',            -- 核心要点列表
    
    -- 评估结果 (二元标签)
    is_important        BOOLEAN DEFAULT NULL,          -- 重要性: true=重要, false=不重要
    is_relevant         BOOLEAN DEFAULT NULL,          -- 相关性: true=相关, false=不相关
    is_interested       BOOLEAN DEFAULT NULL,          -- 用户兴趣: true=感兴趣, false=不感兴趣
    is_downloaded       BOOLEAN DEFAULT FALSE,         -- 是否已下载
    is_read             BOOLEAN DEFAULT FALSE,         -- 是否已读
    
    -- 用户标签
    user_tags           JSONB DEFAULT '[]',            -- 用户自定义标签
    
    -- 时间信息
    published_date      DATE,                          -- 论文发布日期
    processed_date      DATE DEFAULT CURRENT_DATE,     -- 处理日期
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_papers_arxiv_id ON papers(arxiv_id);
CREATE INDEX idx_papers_title ON papers(title);
CREATE INDEX idx_papers_processed_date ON papers(processed_date);
CREATE INDEX idx_papers_is_downloaded ON papers(is_downloaded);
```

### 3. projects — GitHub 项目表

```sql
CREATE TABLE projects (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_id           VARCHAR(200) UNIQUE,          -- owner/repo 格式 (如 "langchain-ai/langchain")
    name                VARCHAR(200) NOT NULL,         -- 项目名称
    full_name           VARCHAR(400),                  -- 完整名称 (owner/name)
    description         TEXT,                          -- 项目描述
    description_cn      TEXT,                          -- 中文描述
    readme_content      TEXT,                          -- README 原始内容
    readme_summary      TEXT,                          -- AI 总结
    source_url          TEXT,                          -- GitHub 地址
    local_readme_path   TEXT,                          -- 本地 README 路径
    
    -- 项目元数据
    stars               INTEGER DEFAULT 0,             -- Star 数
    forks               INTEGER DEFAULT 0,             -- Fork 数
    language            VARCHAR(50),                   -- 主要编程语言
    topics              JSONB DEFAULT '[]',            -- 项目主题标签
    license             VARCHAR(100),                  -- 开源协议
    
    -- 评估结果
    is_important        BOOLEAN DEFAULT NULL,
    is_relevant         BOOLEAN DEFAULT NULL,
    is_interested       BOOLEAN DEFAULT NULL,
    is_downloaded       BOOLEAN DEFAULT FALSE,
    is_read             BOOLEAN DEFAULT FALSE,
    
    -- 用户标签
    user_tags           JSONB DEFAULT '[]',
    
    -- 时间信息
    pushed_at           TIMESTAMP,                     -- 最后推送时间
    processed_date      DATE DEFAULT CURRENT_DATE,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_projects_github_id ON projects(github_id);
CREATE INDEX idx_projects_name ON projects(name);
CREATE INDEX idx_projects_processed_date ON projects(processed_date);
CREATE INDEX idx_projects_stars ON projects(stars DESC);
```

### 4. news — 新闻表

```sql
CREATE TABLE news (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title               TEXT NOT NULL,                 -- 新闻标题
    title_cn            TEXT,                          -- 中文标题
    summary             TEXT,                          -- AI 摘要
    
    -- 来源信息
    source_name         VARCHAR(100),                  -- 来源网站名称
    source_url          TEXT,                          -- 原始链接
    author              VARCHAR(200),                  -- 作者
    local_path          TEXT,                          -- 本地保存路径
    
    -- 评估结果
    is_important        BOOLEAN DEFAULT NULL,
    is_relevant         BOOLEAN DEFAULT NULL,
    is_interested       BOOLEAN DEFAULT NULL,
    is_downloaded       BOOLEAN DEFAULT FALSE,
    is_read             BOOLEAN DEFAULT FALSE,
    
    -- 用户标签
    user_tags           JSONB DEFAULT '[]',
    
    -- 时间信息
    published_at        TIMESTAMP,                     -- 发布时间
    processed_date      DATE DEFAULT CURRENT_DATE,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_news_title ON news(title);
CREATE INDEX idx_news_source ON news(source_name);
CREATE INDEX idx_news_processed_date ON news(processed_date);
CREATE INDEX idx_news_published_at ON news(published_at DESC);
```

### 5. materials — 资料汇总表

```sql
CREATE TABLE materials (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_type           VARCHAR(20) NOT NULL CHECK (item_type IN ('paper', 'project', 'news')),
    item_id             UUID NOT NULL,                 -- 对应 papers/projects/news 表的 id
    title               TEXT NOT NULL,
    summary             TEXT,
    source_url          TEXT,
    
    -- 评估结果
    is_important        BOOLEAN,
    is_relevant         BOOLEAN,
    is_interested       BOOLEAN,
    is_downloaded       BOOLEAN DEFAULT FALSE,
    
    -- 关联
    user_id             UUID REFERENCES users(id),
    
    -- 时间信息
    processed_date      DATE DEFAULT CURRENT_DATE,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_materials_user_date ON materials(user_id, processed_date);
CREATE INDEX idx_materials_type ON materials(item_type);
CREATE INDEX idx_materials_item ON materials(item_type, item_id);

-- 自动同步触发器: 当 papers/projects/news 插入时自动同步到 materials
CREATE OR REPLACE FUNCTION sync_to_materials()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO materials (item_type, item_id, title, summary, source_url, is_important, is_relevant, is_interested, is_downloaded, processed_date)
    VALUES (
        TG_ARGV[0],
        NEW.id,
        NEW.title,
        NEW.summary,
        NEW.source_url,
        NEW.is_important,
        NEW.is_relevant,
        NEW.is_interested,
        NEW.is_downloaded,
        NEW.processed_date
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sync_paper_to_materials
    AFTER INSERT ON papers
    FOR EACH ROW EXECUTE FUNCTION sync_to_materials('paper');

CREATE TRIGGER sync_project_to_materials
    AFTER INSERT ON projects
    FOR EACH ROW EXECUTE FUNCTION sync_to_materials('project');

CREATE TRIGGER sync_news_to_materials
    AFTER INSERT ON news
    FOR EACH ROW EXECUTE FUNCTION sync_to_materials('news');
```

### 6. user_labels — 用户打标记录表

```sql
CREATE TABLE user_labels (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES users(id),
    item_type           VARCHAR(20) NOT NULL CHECK (item_type IN ('paper', 'project', 'news')),
    item_id             UUID NOT NULL,
    label               VARCHAR(20) NOT NULL CHECK (label IN ('interested', 'not_interested', 'read', 'starred')),
    created_at          TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(user_id, item_type, item_id, label)
);

CREATE INDEX idx_user_labels_user ON user_labels(user_id);
CREATE INDEX idx_user_labels_item ON user_labels(item_type, item_id);
```

## 完整建库脚本

```sql
-- 创建数据库
CREATE DATABASE selfautoscholar
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'Chinese (Simplified)_China.936'
    LC_CTYPE = 'Chinese (Simplified)_China.936'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

-- 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 然后执行上述所有 CREATE TABLE 语句
```

## ER 关系图

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   users     │       │   papers    │       │  projects   │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │       │ id (PK)     │
│ username    │       │ arxiv_id    │       │ github_id   │
│ email       │       │ title       │       │ name        │
│ interest_   │       │ abstract    │       │ description │
│   profile   │       │ summary     │       │ readme_     │
│ preferences │       │ is_important│       │   summary   │
└──────┬──────┘       │ is_relevant │       │ stars       │
       │              │ is_interested│      │ is_important│
       │              └──────┬──────┘       └──────┬──────┘
       │                     │                     │
       │    ┌────────────────┼─────────────────────┘
       │    │                │
       │    ▼                ▼
       │  ┌─────────────────────────────┐
       │  │        materials            │
       │  ├─────────────────────────────┤
       │  │ id (PK)                     │
       │  │ item_type (paper/project/   │
       │  │            news)            │
       │  │ item_id (FK)                │
       │  │ title, summary, source_url  │
       │  │ is_important, is_relevant   │
       │  │ is_interested, is_downloaded│
       │  │ user_id (FK)                │
       │  └─────────────────────────────┘
       │                     ▲
       │                     │
       │              ┌──────┴──────┐
       │              │    news     │
       │              ├─────────────┤
       │              │ id (PK)     │
       │              │ title       │
       │              │ summary     │
       │              │ source_name │
       │              │ is_important│
       │              └─────────────┘
       │
       ▼
┌─────────────────────┐
│    user_labels      │
├─────────────────────┤
│ id (PK)             │
│ user_id (FK)        │
│ item_type           │
│ item_id             │
│ label (interested/  │
│   not_interested/   │
│   read/starred)     │
└─────────────────────┘
```
