# 数据库设计

## 4 表概述

| 表 | 主键 | 关键字段 | 本地文件 |
|----|------|---------|---------|
| `textbooks` | UUID | course, title, author, language, local_pdf_path, local_solution_path | `dataset/textbooks/` |
| `papers` | UUID | arxiv_id (UNIQUE), title, authors, categories, local_path | `dataset/papers/` |
| `official_docs` | UUID | name, version, source_url, local_path | `dataset/official_docs/` |
| `resources` | UUID | resource_type, title, url, course_tags, platform | 无 |

## 表结构

### textbooks

```sql
CREATE TABLE textbooks (
    id VARCHAR PRIMARY KEY,
    course VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    author VARCHAR(200),
    language VARCHAR(10) DEFAULT 'zh',
    source VARCHAR(100),
    source_url TEXT,
    local_pdf_path TEXT,
    local_solution_path TEXT,
    stage VARCHAR(20),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_textbooks_course ON textbooks(course);
```

### papers

```sql
CREATE TABLE papers (
    id VARCHAR PRIMARY KEY,
    arxiv_id VARCHAR(50) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    title_cn TEXT,
    authors JSONB DEFAULT '[]',
    categories JSONB DEFAULT '[]',
    published_date DATE,
    source_url TEXT,
    local_path TEXT,
    course_tags JSONB DEFAULT '[]',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_papers_arxiv ON papers(arxiv_id);
```

### official_docs

```sql
CREATE TABLE official_docs (
    id VARCHAR PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    version VARCHAR(50),
    source_url TEXT,
    local_path TEXT,
    pages_count INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_docs_name ON official_docs(name);
```

### resources

```sql
CREATE TABLE resources (
    id VARCHAR PRIMARY KEY,
    resource_type VARCHAR(20) NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    description TEXT,
    course_tags JSONB DEFAULT '[]',
    author VARCHAR(200),
    platform VARCHAR(100),
    is_favorite BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_resources_type ON resources(resource_type);
```

## 仓储层

```
BaseRepository[T] → CRUD (get/list/create/update/delete/count/exists)
├── TextbookRepo    (+ get_by_course, exists_by_path)
├── PaperRepo       (+ get_by_arxiv_id, exists_by_arxiv_id)
├── OfficialDocRepo (+ get_by_name)
└── ResourceRepo    (+ get_by_type)
```

## 连接池

```
pool_size=5, max_overflow=10, pool_pre_ping=True, pool_recycle=3600
```
