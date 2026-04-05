#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 1: LM Studio 本地模型对话测试

目标: 验证 LM Studio 本地部署的 LLM 可以正常对话
模型地址: http://127.0.0.1:5001
问题: "你是谁，请介绍你的能力"

运行方式:
    python test/test_lmstudio_chat.py
"""

from __future__ import print_function
from openai import OpenAI


def test_lmstudio_chat():
    """向 LM Studio 本地模型发送问题并打印回答"""

    # ============================================================
    # 步骤 1: 创建 OpenAI 客户端，指向本地 LM Studio 服务
    # ============================================================
    # LM Studio 兼容 OpenAI API 格式，所以可以直接用 OpenAI SDK
    # base_url 是 LM Studio 的服务地址
    client = OpenAI(
        base_url="http://127.0.0.1:5001/v1",  # LM Studio 服务地址
        api_key="not-needed",                   # 本地服务不需要 API Key
    )

    # ============================================================
    # 步骤 2: 定义用户问题
    # ============================================================
    question = "你是谁，你能帮我做什么？"
    print(f"向 LM Studio 发送问题: {question}")
    print("-" * 60)

    # ============================================================
    # 步骤 3: 调用本地模型进行对话
    # ============================================================
    # model 参数: LM Studio 会自动使用当前加载的模型，这里填任意非空字符串即可
    # temperature=0.7: 控制回答的随机性 (0=确定, 1=更有创意)
    # max_tokens=1024: 限制最大回答长度
    response = client.chat.completions.create(
        model="local-model",
        messages=[
            {"role": "user", "content": question},
        ],
        temperature=0.7,
        max_tokens=1024,
    )

    # ============================================================
    # 步骤 4: 提取并打印模型回答
    # ============================================================
    answer = response.choices[0].message.content
    print(f"\n模型回答:\n{answer}")

    # ============================================================
    # 步骤 5: 打印请求统计信息
    # ============================================================
    usage = response.usage
    print(f"\n--- 请求统计 ---")
    print(f"输入 tokens: {usage.prompt_tokens}")
    print(f"输出 tokens: {usage.completion_tokens}")
    print(f"总 tokens:   {usage.total_tokens}")

    return answer


if __name__ == "__main__":
    answer = test_lmstudio_chat()
    print(f"\n测试通过! answer = {answer}")

