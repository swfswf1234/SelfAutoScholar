# 系统架构

## 全景

```mermaid
graph TB
    subgraph "配置"
        CFG[setting.ini] --> CORE[app/core/config.py]
    end

    subgraph "数据库"
        CORE --> PG[(PostgreSQL)]
        PG --> INIT[init_db.py 建库]
    end

    subgraph "采集层"
        PC[PaperCollector<br/>app/collectors/paper_collector.py] -->|arXiv API| ARX[(arXiv 论文)]
        TH[TextbookHunter<br/>app/collectors/textbook_hunter.py] -->|LibGen| LG[(libgen.is 教材)]
        DS[DocScraper<br/>app/collectors/doc_scraper.py] -->|wget| WGET[(官网 HTML)]
    end

    subgraph "存储"
        PC -->|PDF| PD[dataset/papers/{year}/]
        TH -->|PDF| TD[dataset/textbooks/{course}/]
        DS -->|HTML| OD[dataset/official_docs/{name}/]
    end

    subgraph "索引"
        PD -->|元数据| PG
        TD -->|元数据| PG
        OD -->|元数据| PG
        SCAN[scan_dataset.py] -->|扫描已有| PG
    end

    subgraph "CLI 入口"
        HP[scripts/hunt_papers.py]
        HT[scripts/hunt_textbooks.py]
        HD[scripts/hunt_docs.py]
        HP --> PC
        HT --> TH
        HD --> DS
    end
```

## 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| **PaperCollector** | `app/collectors/paper_collector.py` | arXiv 搜索 → 交互确认 → PDF 下载 |
| **TextbookHunter** | `app/collectors/textbook_hunter.py` | LibGen 搜索 → 交互确认 → PDF 下载 |
| **DocScraper** | `app/collectors/doc_scraper.py` | wget --mirror 爬取官方文档 |
| **Config** | `app/core/config.py` | 从 setting.ini 读取配置 |
| **Database** | `app/core/database.py` | 连接池 + Session + 建表 |
| **Repository** | `app/repository/` | 4 表 CRUD 封装 |
| **Models** | `app/models/` | SQLAlchemy ORM 模型 |
| **arXiv Client** | `app/services/arxiv_client.py` | arXiv API 调用封装 |

## 数据库

4 张 PostgreSQL 表：

| 表 | 存储内容 | 本地文件 |
|----|---------|---------|
| `textbooks` | 教材元数据 + 路径 | `dataset/textbooks/` |
| `papers` | 论文元数据 + 路径 | `dataset/papers/` |
| `official_docs` | 文档元数据 + 路径 | `dataset/official_docs/` |
| `resources` | 链接类资源 (仅存 PG) | 无 |

## 5 个 CLI 入口

```bash
init_db.py --create-db       # 建库 + 4 表 (幂等)
scan_dataset.py              # 扫描已有文件入库
hunt_textbooks.py            # 遍历课程检索教材
hunt_papers.py --domain X    # arXiv 论文检索
hunt_docs.py --name X        # 官方文档爬取
```
