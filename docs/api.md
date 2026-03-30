# API 接口设计

本接口面向自用场景，使用 API Key 进行鉴权，暴露“查询模板/参数化查询”能力，以及标注与 Markdown 导出能力，便于与本地知识库无缝接入。

## 认证
- 请求头包含 API Key：`X-API-Key: <your-api-key>`
- 服务端校验失败返回 401/403，禁止访问。

## 1) 查询模板（Templates）
- GET /templates
- POST /templates
- GET /templates/{id}
- 作用：管理参数化查询的模板，模板字段包括模板名称、字段定义、默认参数等。

## 2) 执行查询（Queries）
- POST /queries/execute
- 请求体示例
  {
    "template_id": "<template-id>",
    "parameters": {
      "keywords": ["arXiv:cs.*"],
      "date_from": "2026-01-01",
      "sources": ["arxiv"],
      "filters": {"min_relevance": 0.2}
    },
    "user_id": "<user-id>"
  }
- 响应示例
  {
    "items": [
      {
        "item_type": "paper",
        "item_id": "<paper-id>",
        "title": "Example Paper Title",
        "summary": "摘要要点",
        "source_url": "https://arxiv.org/abs/xxxx.xxxxx",
        "relevance": 0.75
      }
    ]
  }
- 说明：该接口执行参数化查询并返回候选项，后续下载与处理由本地工作流决定。

## 3) 标注（Labels）
- POST /labels
- 请求体示例
  {
    "user_id": "<user-id>",
    "item_type": "paper",
    "item_id": "<paper-id>",
    "label": "interested"  # 值可为：interested, not_interested, unsure, read
  }
- POST /labels/batch
- 请求体示例
  {
    "user_id": "<user-id>",
    "labels": [
      {"item_type": "paper", "item_id": "<id1>", "label": "interested"},
      {"item_type": "paper", "item_id": "<id2>", "label": "read"}
    ]
  }
- 作用：方便用户快速标注单条或批量条目，以驱动个性化推荐。

## 4) Markdown 导出（Export Markdown）
- POST /export/markdown
- 请求体示例
  {
    "user_id": "<user-id>",
    "scope": ["papers", "explorations", "useful_items"],
    "format": "markdown"
  }
- 响应示例
  {
    "export_path": "/path/to/exports/user-<id>/2026-03-30/summary.md",
    "summary": "Markdown 文档生成成功"
  }
- 作用：将筛选后的数据整理为 Markdown 文档，便于知识库落地。

## 备注
- 以上接口设计面向小型自用场景，参数结构可按需调整。
- 如需扩展为多租户或公开 API，请告知以添加相应授权、配额和审计字段。
