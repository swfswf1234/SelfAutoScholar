# SelfAutoScholar

SelfAutoScholar 是一个本地部署的每日资讯聚合系统，自动从 arXiv、GitHub、RSS 新闻源抓取你可能感兴趣的内容，经过去重、筛选、分析后生成结构化简报，并支持 Obsidian 知识库同步。

为未来的**个人知识库构建**和**知识讲解 Agent** 提供高质量、已清洗、结构化的底层数据。

## 核心功能 | Core Features

| 功能 | 说明 |
|------|------|
| 论文发现 | 通过 arXiv API 检索最新论文，按领域/关键词匹配 |
| 项目追踪 | GitHub 热门项目发现，评估功能与价值 |
| 新闻聚合 | RSS/可信科技媒体新闻抓取与分析 |
| 智能去重 | 标题、DOI、URL 多维度去重，避免重复推送 |
| 重要性评估 | 外部 LLM 评估内容重要性与用户相关性 (1-10 分) |
| PDF 深度解析 | PDF → Markdown 转换，含图表提取与外文翻译 |
| 内容摘要 | AI 生成论文观点、项目价值、新闻要点摘要 |
| 兴趣迭代 | 根据用户打标行为自动优化推荐偏好 |
| Obsidian 同步 | 用户画像、阅读记录、知识标签同步至 Obsidian Vault |

## 技术栈 | Tech Stack

| 组件 | 技术选型 | 用途 |
|------|----------|------|
| Web 框架 | FastAPI | REST API 接口 |
| 数据库 | PostgreSQL + SQLAlchemy | 数据持久化 |
| 本地 LLM | LM Studio | 下载、翻译、总结 |
| 外部 LLM | OpenAI 兼容 API | 深度推理、重要性评分 |
| MCP 协议 | mcp SDK | 网络资料搜索增强 |
| PDF 处理 | pymupdf4llm | PDF → LLM 友好格式 |
| 任务调度 | APScheduler | 每日定时执行 |
| 知识库 | Obsidian (Markdown) | 用户偏好、知识图谱 |

## 系统架构 | Architecture

> 详见 [docs/architecture.md](docs/architecture.md)

## 安装指南 | Installation

> 详见 [docs/installation.md](docs/installation.md)

**环境要求：**
- Python 3.10+
- PostgreSQL 14+
- LM Studio (本地 LLM 部署)
- Obsidian (可选，用于知识库同步)

**快速安装：**
```bash
git clone <repo-url>
cd SelfAutoScholar
pip install -r requirements.txt
```

## 配置说明 | Configuration
配置文件为 `setting.ini`，包含数据库连接、MCP 服务地址、API Key、本地模型路径等。

## 数据库设计 | Database Schema

> 详见 [docs/database.md](docs/database.md)

核心表结构：
- `users` — 用户信息与兴趣画像
- `papers` — 论文数据 (含摘要、评分、用户标签)
- `projects` — GitHub 项目数据
- `news` — 新闻数据
- `materials` — 资料汇总视图
- `user_labels` — 用户打标记录

## 使用指南 | Usage Guide

> 详见 [docs/api.md](docs/api.md)


## 开发计划 | Roadmap

- [ ] MVP: arXiv 论文每日抓取与筛选
- [ ] GitHub 项目发现与评估
- [ ] RSS 新闻聚合
- [ ] PDF 深度解析 (pymupdf4llm)
- [ ] 用户打标与兴趣迭代
- [ ] Obsidian 知识库同步
- [ ] 每日 Markdown 简报自动生成

## 许可证 | License

[MIT](LICENSE)
