"""LLM 评估服务"""

import json
from openai import OpenAI
from loguru import logger


EVAL_PROMPT = """你是一个学术论文评估助手。请评估以下论文，返回 JSON 格式结果。

标题: {title}

摘要: {abstract}

评估标准:
1. is_important (重要性): 该论文是否在 AI/ML/NLP/CV 领域有重要贡献？是否有新颖的方法或发现？
2. is_relevant (相关性): 是否与以下领域相关: 大语言模型 (LLM)、自然语言处理 (NLP)、机器学习、深度学习、计算机视觉？
3. is_interested (兴趣度): 基于摘要内容，该论文是否值得深入阅读？是否有实用价值或理论突破？

请返回严格 JSON 格式 (不要添加其他文字):
{{"is_important": true/false, "is_relevant": true/false, "is_interested": true/false}}"""


def evaluate_paper(client: OpenAI, model: str, title: str, abstract: str) -> dict:
    """
    调用 LLM 评估单篇论文

    Args:
        client: OpenAI 客户端
        model: 模型名称
        title: 论文标题
        abstract: 论文摘要

    Returns:
        评估结果 dict: {"is_important": bool, "is_relevant": bool, "is_interested": bool}
    """
    try:
        prompt = EVAL_PROMPT.format(title=title, abstract=abstract[:2000])  # 截断过长摘要

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=100,
        )

        content = response.choices[0].message.content.strip()

        # 尝试解析 JSON
        # 处理可能的 markdown 代码块
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(content)

        # 验证返回格式
        return {
            "is_important": bool(result.get("is_important", False)),
            "is_relevant": bool(result.get("is_relevant", False)),
            "is_interested": bool(result.get("is_interested", False)),
        }
    except Exception as e:
        logger.warning(f"LLM 评估失败: {title[:50]}... | 错误: {e}")
        # 默认返回不重要、不相关、不感兴趣
        return {"is_important": False, "is_relevant": False, "is_interested": False}


def evaluate_papers(client: OpenAI, model: str, papers: list[dict]) -> list[dict]:
    """
    批量评估论文

    Args:
        client: OpenAI 客户端
        model: 模型名称
        papers: 论文列表 (需含 title, abstract)

    Returns:
        添加了 evaluation 字段的论文列表
    """
    logger.info(f"开始评估 {len(papers)} 篇论文 (模型: {model})")

    for i, paper in enumerate(papers):
        paper["evaluation"] = evaluate_paper(client, model, paper["title"], paper["abstract"])
        logger.debug(f"[{i+1}/{len(papers)}] {paper['title'][:50]}... → {paper['evaluation']}")

    logger.info("评估完成")
    return papers


def should_download(evaluation: dict) -> bool:
    """
    判断是否应该下载

    规则: is_important AND (is_relevant OR is_interested)
    """
    is_important = evaluation.get("is_important", False)
    is_relevant = evaluation.get("is_relevant", False)
    is_interested = evaluation.get("is_interested", False)

    return is_important and (is_relevant or is_interested)
