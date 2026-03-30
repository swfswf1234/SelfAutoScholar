self_auto_schola/
├── app/
│   ├── api/                  # FastAPI 路由，暴露打标接口和查询接口
│   │   ├── endpoints/
│   │   │   ├── papers.py
│   │   │   ├── materials.py
│   │   │   └── users.py
│   ├── core/                 # 核心配置
│   │   ├── config.py         # 环境变量、LM Studio 地址、API Keys 配置
│   │   └── database.py       # SQLAlchemy 引擎和 Session 管理
│   ├── models/               # 数据库 ORM 模型
│   │   ├── user.py
│   │   ├── raw_material.py
│   │   └── paper.py
│   ├── schemas/              # Pydantic 验证模型 (用于 API 输入输出)
│   ├── services/             # 业务逻辑层
│   │   ├── local_mcp_client.py # 对接 LM Studio + mcp.json 工具调用
│   │   ├── external_llm.py   # OpenAI / 外部大模型封装
│   │   └── pdf_processor.py  # 基于 Torch 的 PDF 结构化解析
│   ├── agents/               # LangChain Agent 定义
│   │   ├── discovery_agent.py  # 负责搜集、过滤、去重并选出 Top 10
│   │   ├── analysis_agent.py   # 负责翻译、总结、分析观点
│   │   └── interest_agent.py   # 负责根据打标结果反思并迭代用户偏好
│   └── main.py               # FastAPI 实例入口与定时任务挂载
├── data/
│   └── downloads/            # 本地 PDF 存储目录 (按年/月/日划分)
├── tests/
├── docs/
├── requirements.txt
├── setting.ini
└── README.md
