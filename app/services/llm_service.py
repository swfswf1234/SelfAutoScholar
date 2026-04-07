"""统一 LLM 服务 - 同时支持本地 (LM Studio) 和外部 (OpenAI) LLM 调用

功能说明:
    - 根据配置自动选择使用本地或外部 LLM
    - 支持论文评估、关键词提取、摘要总结等多种任务
    - 自动处理 Qwen 等思维链模型的 reasoning_content 提取

配置项 (setting.ini [LLM] 节点):
    evaluation_provider  - 论文评估任务使用哪个 provider (local / external)
    reasoning_provider  - 推理分析任务使用哪个 provider (local / external)
    local_api_base     - 本地 LLM 地址 (如 http://127.0.0.1:5001/v1)
    local_api_key      - 本地 LLM API Key
    local_model        - 本地 LLM 模型名
    external_api_base  - 外部 LLM 地址 (如 https://api.openai.com/v1)
    external_api_key   - 外部 LLM API Key
    external_model     - 外部 LLM 模型名
"""

import json
import re

from openai import OpenAI

from app.core.config import settings


def should_download(evaluation: dict) -> bool:
    """
    判断是否应该下载。
    规则: is_important AND (is_relevant OR is_interested)
    """
    is_important = evaluation.get("is_important", False)
    is_relevant = evaluation.get("is_relevant", False)
    is_interested = evaluation.get("is_interested", False)
    return is_important and (is_relevant or is_interested)


EVALUATION_PROMPT = """你是一个学术论文评估助手。请评估以下论文，返回严格 JSON 格式结果（不要添加其他文字）。

标题: {title}

摘要: {abstract}

评估标准:
1. is_important (重要性): 该论文是否在 AI/ML/NLP/CV 领域有重要贡献？是否有新颖的方法或发现？
2. is_relevant (相关性): 是否与以下领域相关: 大语言模型 (LLM)、自然语言处理 (NLP)、机器学习、深度学习、计算机视觉？
3. is_interested (兴趣度): 基于摘要内容，该论文是否值得深入阅读？是否有实用价值或理论突破？

返回格式（严格 JSON，不要其他内容）:
{{"is_important": true/false, "is_relevant": true/false, "is_interested": true/false}}"""

SYSTEM_MSG_DISABLE_THINKING = (
    "你是一个严谨的助手。请直接回答用户问题，不要输出任何思考过程、推理步骤或Thinking Process。只输出最终答案。"
)


def _build_client(provider: str) -> tuple[OpenAI, str]:
    """
    根据 provider 名称创建 OpenAI 客户端并返回 (client, model_name)。

    Args:
        provider: "local" 或 "external"

    Returns:
        (OpenAI client, model_name)
    """
    if provider == "local":
        client = OpenAI(
            base_url=settings.local_llm_api_base,
            api_key=settings.local_llm_api_key or "not-needed",
            timeout=120.0,
        )
        return client, settings.local_llm_model
    else:
        client = OpenAI(
            base_url=settings.llm_api_base,
            api_key=settings.llm_api_key,
            timeout=60.0,
        )
        return client, settings.llm_model


def _extract_json_from_response(response_text: str) -> dict | None:
    """
    从 LLM 响应中提取 JSON。
    支持: 原始 JSON、markdown 代码块、从 reasoning_content 中提取。

    Args:
        response_text: LLM 返回的原始文本

    Returns:
        解析后的 dict，失败返回 None
    """
    text = response_text.strip()
    if not text:
        return None

    try:
        return json.loads(text)
    except Exception:
        pass

    start_idx = text.rfind('{"is_important":')
    if start_idx == -1:
        start_idx = text.find('"is_important":')
    if start_idx == -1:
        return None

    brace_start = text.rfind("{", 0, start_idx + 1)
    if brace_start == -1:
        return None

    for end_idx in range(len(text) - 1, brace_start, -1):
        try:
            candidate = text[brace_start:end_idx + 1]
            parsed = json.loads(candidate)
            if all(k in parsed for k in ("is_important", "is_relevant", "is_interested")):
                return parsed
        except Exception:
            continue

    return None


def _call_llm(client: OpenAI, model: str, prompt: str, system_msg: str = "") -> dict:
    """
    通用 LLM 调用封装，处理 reasoning_content 和 JSON 提取。

    Args:
        client: OpenAI 客户端
        model: 模型名
        prompt: 用户 prompt
        system_msg: 系统消息（可选）

    Returns:
        {"is_important": bool, "is_relevant": bool, "is_interested": bool}
    """
    messages = []
    if system_msg:
        messages.append({"role": "system", "content": system_msg})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
        max_tokens=4000,
    )

    raw_content = response.choices[0].message.content or ""
    reasoning = getattr(response.choices[0].message, "reasoning_content", "") or ""
    combined = raw_content.strip() or reasoning.strip()

    result = _extract_json_from_response(combined)
    if result:
        return {
            "is_important": bool(result.get("is_important", False)),
            "is_relevant": bool(result.get("is_relevant", False)),
            "is_interested": bool(result.get("is_interested", False)),
        }

    return {"is_important": False, "is_relevant": False, "is_interested": False}


class LLMService:
    """
    统一 LLM 服务。

    Usage:
        service = LLMService()
        service.evaluate_papers(papers)
        service.extract_keywords(abstract)
        service.summarize_abstract(abstract)
    """

    def __init__(self, provider: str | None = None):
        """
        初始化 LLM 服务。

        Args:
            provider: 强制指定 provider ("local" / "external")，
                     为 None 时使用 setting.ini 中的 evaluation_provider 配置
        """
        self.provider = provider or settings.evaluation_provider
        self.client, self.model = _build_client(self.provider)

    def __repr__(self):
        return "LLMService(provider={}, model={})".format(self.provider, self.model)

    def evaluate_paper(self, title: str, abstract: str) -> dict:
        """
        评估单篇论文。

        Args:
            title: 论文标题
            abstract: 论文摘要

        Returns:
            {"is_important": bool, "is_relevant": bool, "is_interested": bool}
        """
        prompt = EVALUATION_PROMPT.format(title=title, abstract=abstract[:2000])
        return _call_llm(self.client, self.model, prompt, SYSTEM_MSG_DISABLE_THINKING)

    def evaluate_papers(self, papers: list[dict]) -> list[dict]:
        """
        批量评估论文。

        Args:
            papers: 论文列表，每个需含 title 和 abstract 字段

        Returns:
            添加了 evaluation 字段的论文列表

        Usage:
            service = LLMService()
            papers = [{"title": "...", "abstract": "..."}]
            service.evaluate_papers(papers)
        """
        print("[LLMService] 评估论文 (provider={}, model={})".format(self.provider, self.model))
        for i, paper in enumerate(papers):
            title = paper["title"]
            try:
                paper["evaluation"] = self.evaluate_paper(title, paper["abstract"])
            except Exception as e:
                paper["evaluation"] = {"is_important": False, "is_relevant": False, "is_interested": False}

            ev = paper["evaluation"]
            dl = should_download(ev)
            print("  [{}/{}] {} -> 重要={} 相关={} 有趣={} | 下载={}".format(
                i + 1, len(papers), title[:50],
                ev["is_important"], ev["is_relevant"], ev["is_interested"],
                "是" if dl else "否"
            ))
        return papers

    def extract_keywords_and_summary(self, text: str, max_keywords: int = 10) -> dict:
        """
        用 LLM 提取关键词和生成核心观点摘要。

        Args:
            text: 输入文本（摘要等）
            max_keywords: 返回关键词数量

        Returns:
            {
                "keywords": ["keyword1", "keyword2", ...],
                "summary": "核心观点摘要..."
            }
        """
        prompt = (
            "请分析以下论文摘要，提取 {} 个关键词（用逗号分隔），"
            "并生成一句话核心观点摘要（不超过 100 字）。\n\n"
            "返回严格 JSON 格式（不要添加其他文字）：\n"
            '{{"keywords": ["keyword1", "keyword2", ...], "summary": "核心观点..."}}\n\n'
            "论文摘要:\n{}"
        ).format(max_keywords, text[:4000])

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_MSG_DISABLE_THINKING},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            raw = response.choices[0].message.content or ""
            reasoning = getattr(response.choices[0].message, "reasoning_content", "") or ""
            combined = raw.strip() or reasoning.strip()

            if combined:
                result = json.loads(combined)
                return {
                    "keywords": result.get("keywords", [])[:max_keywords],
                    "summary": result.get("summary", "")[:200],
                }
        except Exception:
            pass

        return {"keywords": [], "summary": text[:200]}
