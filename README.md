# SelfAutoScholar 🧠

SelfAutoScholar 是一个用于每日从网上拉取你可能关注的论文、感兴趣的 GitHub 项目与新闻，并将数据整理成 Markdown 格式存入数据库的本地知识源系统。

本项目旨在为未来的**个人知识库构建**和**知识讲解Agent**提供高质量、已清洗、结构化的底层数据。

## 🚀 核心特性

* **混合模型架构**：通过 MCP 协议调用本地LLM完成搜索、抓取、下载等动作；调用外部大模型 API 进行深度推理、重要性打分和翻译。
* **智能去重与限流**：严格确保推荐内容的唯一性，每日精准推送 Top 10 最具价值的信息。
* **深度文档解析**：利用 PyTorch 与相关文档处理模型（阿里Logics-Parsing模型处理扫描件，pdfplumber处理文本型），将 PDF 转换为适用于大模型阅读的高质量格式（包含图表解析和外文转中文）。
* **自适应兴趣迭代**：记录用户阅读反馈（感兴趣/不感兴趣），系统通过反思机制自动更新推荐偏好 Prompt。

## 🛠 架构简览
- 通过 docs/architecture.md 了解核心组件、数据流与扩展点。
* **Web 框架**: FastAPI
* **大模型编排**: LangChain
* **文档处理**: Logics-Parsing/pdfplumber
* **数据库**: PostgreSQL

## 📦 快速开始
* 依赖 PostgreSQL、Python 环境、MCP 本地服务（API Key 认证），以及可选的本地大模型服务。
* 配置示例在 config 文件/环境变量中，包含数据库连接、MCP 基地址、API Key、以及本地模型路径。
* 运行方式请参考 docs/api.md 及 docs/architecture.md 的指引。

## 进一步阅读
* 文档：docs/api.md（公开接口设计）