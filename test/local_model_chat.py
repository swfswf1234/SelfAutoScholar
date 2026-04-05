#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试: LM Studio 本地模型对话测试（精简版）

目标: 验证 LM Studio 本地部署的 LLM 可以正常对话
模型地址: http://127.0.0.1:5001

运行方式:
    python test/local_model_chat.py
"""

from __future__ import print_function

from openai import OpenAI

# ============================================================
# 步骤 1: 创建 OpenAI 客户端，指向本地 LM Studio 服务
# ============================================================
client = OpenAI(
    base_url="http://127.0.0.1:5001/v1",
    api_key="not-needed",
)

question = "你是谁，你能帮我做什么？"
print("向 LM Studio 发送问题: {}".format(question))
print("-" * 60)

# ============================================================
# 步骤 2: 调用本地模型进行对话
# ============================================================
response = client.chat.completions.create(
    model="qwen/qwen3.5-9b",
    messages=[
        {"role": "user", "content": question},
    ],
    temperature=0.7,
    max_tokens=1024,
)

# ============================================================
# 步骤 3: 提取并打印模型回答
# ============================================================
answer = response.choices[0].message.content
print("\n模型回答:\n{}".format(answer))
