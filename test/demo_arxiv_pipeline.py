#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
demo_arxiv_pipeline.py - 从 arXiv 下载论文并分析的完整流程演示

功能概述:
    1. 按 arXiv ID 或关键词搜索论文元数据
    2. 调用本地 LLM (LM Studio) 评估论文重要性/相关性/兴趣度
    3. 根据评估结果判断是否下载 PDF
    4. 下载 PDF 并用论文标题重命名
    5. 引用估算 + 摘要关键词分析
    6. 导出 JSON 分析报告
    7. 导出 Markdown 论文列表

使用方式:
    # 方式 1: 指定 arXiv ID（支持多个，逗号分隔）
    python test/demo_arxiv_pipeline.py --arxiv-id 2604.02331
    python test/demo_arxiv_pipeline.py --arxiv-id 2604.02331,2503.21456

    # 方式 2: 关键词搜索（返回最新 5 篇供选择）
    python test/demo_arxiv_pipeline.py --search "large language model reasoning"
    python test/demo_arxiv_pipeline.py --search "transformer attention" --max 10

    # 方式 3: 交互式（无参数运行）
    python test/demo_arxiv_pipeline.py
"""

from __future__ import print_function

import sys
import io
import os
import re
import json
import argparse
from pathlib import Path
from datetime import date
from collections import Counter

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

# ============================================================
# 步骤 1: 导入 app/services 模块
# app/services/ 依赖 loguru 做日志，但 demo 用 print 输出
# 这里先禁用所有 loguru 日志，避免干扰用户输出
# ============================================================
import loguru
loguru.logger.disable("loguru")

import httpx
import arxiv
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.arxiv_client import search_papers
from app.services.llm_evaluator import evaluate_papers, should_download
from app.services.pdf_downloader import download_pdf

# ============================================================
# ============================================================
# 步骤 2: 引用估算器
# 说明: arXiv 本身不提供引用数据，此处基于论文年龄和分类做模拟估算
# ============================================================
from dataclasses import dataclass


@dataclass
class CitationInfo:
    """引用估算结果"""
    estimated_citations: int
    citations_per_year: float
    h_index_contribution: int
    note: str


@dataclass
class Paper:
    """论文数据容器"""
    id: str
    title: str
    authors: list
    abstract: str
    published: str
    categories: list
    arxiv_url: str = ""
    pdf_url: str = ""


class CitationAnalyzer:
    """
    基于论文年龄和分类估算引用指标。
    注意: arXiv 本身不追踪引用数据，结果为模拟估算，仅供参考。
    """

    # 高引用权重分类（AI/ML/NLP/CV 领域通常引用更高）
    HIGH_IMPACT_CATS = {"cs.CL", "cs.AI", "cs.LG", "cs.CV", "cs.NE", "stat.ML"}

    def estimate_citations(self, paper: Paper) -> CitationInfo:
        """估算论文的引用指标"""
        try:
            pub_year = int(paper.published[:4]) if paper.published else 2020
        except (ValueError, TypeError):
            pub_year = 2020

        current_year = 2026
        age_years = max(1, current_year - pub_year)

        has_high_impact = bool(
            paper.categories and self.HIGH_IMPACT_CATS.intersection(set(paper.categories))
        )

        if age_years <= 1:
            base = 50 if has_high_impact else 15
            estimated = int(base * 0.7)
        elif age_years <= 3:
            base = 150 if has_high_impact else 40
            estimated = int(base * (1 - (age_years - 1) * 0.1))
        else:
            base = 300 if has_high_impact else 80
            estimated = int(base * (1 - (age_years - 3) * 0.05))

        estimated = max(1, min(estimated, 999))
        citations_per_year = round(estimated / age_years, 1)
        h_index_contribution = min(estimated, 10)

        note = ("arXiv 不直接追踪引用数，此为基于发表年份和分类的模拟估算。"
                 "高引用分类 (AI/CL/LG/CV) 会获得更高估算值。")

        return CitationInfo(
            estimated_citations=estimated,
            citations_per_year=citations_per_year,
            h_index_contribution=h_index_contribution,
            note=note,
        )


# ============================================================
# 步骤 3: 配置 - LLM 端点
# ============================================================
# 步骤 2: 配置 - LLM 端点
# ============================================================
LM_STUDIO_BASE_URL = os.environ.get("LM_STUDIO_BASE_URL", "http://127.0.0.1:5001/v1")
LM_STUDIO_API_KEY = "not-needed"
LM_STUDIO_MODEL = os.environ.get("LM_STUDIO_MODEL", "qwen/qwen3.5-9b")

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DOWNLOADS_DIR = DATA_DIR / "downloads"


# ============================================================
# 步骤 3: 辅助函数
# ============================================================

def _safe_filename(title: str, max_len: int = 80) -> str:
    """将论文标题转换为安全的文件名"""
    safe = re.sub(r'[<>:"/\\|?*\u0000-\u001f]', "", title)
    safe = re.sub(r'\s+', "_", safe.strip())
    return safe[:max_len].strip("_") or "untitled"


def _build_paper_dict(raw: dict) -> dict:
    """将 arxiv 库返回的原始 dict 转换为标准格式"""
    return {
        "arxiv_id": raw["arxiv_id"],
        "title": raw["title"],
        "abstract": raw["abstract"],
        "authors": raw["authors"],
        "categories": raw.get("categories", []),
        "pdf_url": raw["pdf_url"],
        "source_url": raw["source_url"],
        "published_date": str(raw["published_date"]),
    }


# ============================================================
# 步骤 4: 按 arXiv ID 获取单篇论文元数据
# ============================================================
def fetch_paper_by_id(arxiv_id: str) -> dict | None:
    """
    通过 arXiv ID 获取单篇论文的完整元数据。
    内部使用 arxiv 库查询，确保获取 PDF URL 等完整信息。
    """
    clean_id = re.sub(r'v\d+$', '', arxiv_id)
    print("[步骤 1/7] 通过 arXiv ID '{}' 获取论文元数据...".format(arxiv_id))

    try:
        client = arxiv.Client(page_size=1, delay_seconds=1.0, num_retries=3)
        search = arxiv.Search(
            query=f"id:{clean_id}",
            max_results=1,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        results = list(client.results(search))
        if not results:
            print("  [警告] 未找到 ID 为 {} 的论文".format(arxiv_id))
            return None

        paper = results[0]
        arxiv_id_str = paper.entry_id.split("/abs/")[-1]
        return {
            "arxiv_id": arxiv_id_str,
            "title": paper.title,
            "abstract": paper.summary,
            "authors": [a.name for a in paper.authors],
            "categories": list(paper.categories),
            "pdf_url": paper.pdf_url,
            "source_url": paper.entry_id,
            "published_date": paper.published.date(),
        }
    except Exception as e:
        print("  [错误] 获取论文失败: {}".format(str(e)))
        return None


# ============================================================
# 步骤 5: 按关键词搜索并交互选择
# ============================================================
def search_and_select(keyword: str, max_results: int = 5) -> list[dict]:
    """
    按关键词搜索论文，展示列表供用户选择。
    返回用户选择的论文列表（可多选，逗号分隔序号）。
    """
    print("[步骤 1/7] 搜索 arXiv: 关键词='{}', 最大返回 {} 篇".format(keyword, max_results))
    raw_papers = search_papers(keyword, max_results=max_results, delay=1.0)

    if not raw_papers:
        print("  [警告] 未找到匹配的论文，请尝试其他关键词")
        return []

    print("\n找到以下论文，请输入要处理的序号（逗号分隔，如 1,3,5，回车选择全部）:\n")
    for i, p in enumerate(raw_papers, 1):
        authors_short = ", ".join(p["authors"][:2])
        if len(p["authors"]) > 2:
            authors_short += " et al."
        pub_date = p.get("published_date", "unknown")
        print("  {}. [{}] {}".format(i, pub_date, p["title"][:70]))
        print("     作者: {}".format(authors_short))
        cats = ", ".join(p["categories"][:3])
        print("     分类: {}".format(cats))
        print()

    try:
        choice = input("您的选择 (直接回车 = 全部): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = ""

    if not choice:
        selected = raw_papers
    else:
        indices = []
        for part in choice.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(raw_papers):
                    indices.append(idx)
        selected = [raw_papers[i] for i in sorted(set(indices))]

    print("\n已选择 {} 篇论文".format(len(selected)))
    return selected


# ============================================================
# 步骤 6: 调用 LM Studio 评估论文
# ============================================================
def evaluate_with_lmstudio(papers: list[dict]) -> list[dict]:
    """
    调用本地 LM Studio 对论文进行评估。
    评估三个维度: 重要性(is_important)、相关性(is_relevant)、兴趣度(is_interested)。
    """
    print("\n[步骤 2/7] 调用 LM Studio 评估论文 (端点: {})".format(LM_STUDIO_BASE_URL))
    print("-" * 70)

    client = OpenAI(base_url=LM_STUDIO_BASE_URL, api_key=LM_STUDIO_API_KEY, timeout=120.0)

    for i, paper in enumerate(papers):
        title = paper["title"]
        abstract = paper["abstract"]

        try:
            prompt = """你是一个学术论文评估助手。请评估以下论文，返回严格 JSON 格式结果（不要添加其他文字）。

标题: {title}

摘要: {abstract}

评估标准:
1. is_important (重要性): 该论文是否在 AI/ML/NLP/CV 领域有重要贡献？是否有新颖的方法或发现？
2. is_relevant (相关性): 是否与以下领域相关: 大语言模型 (LLM)、自然语言处理 (NLP)、机器学习、深度学习、计算机视觉？
3. is_interested (兴趣度): 基于摘要内容，该论文是否值得深入阅读？是否有实用价值或理论突破？

返回格式（严格 JSON，不要其他内容）:
{{"is_important": true/false, "is_relevant": true/false, "is_interested": true/false}}""".format(
                title=title, abstract=abstract[:2000]
            )

            print("  正在评估 [{}/{}]: {}...".format(i + 1, len(papers), title[:50]))
            response = client.chat.completions.create(
                model=LM_STUDIO_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个严谨的助手。请直接回答用户问题，不要输出任何思考过程、推理步骤或Thinking Process。只输出最终答案。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=4000,
            )

            raw_content = response.choices[0].message.content or ""
            reasoning = getattr(response.choices[0].message, "reasoning_content", "") or ""
            combined = raw_content.strip() or reasoning.strip()

            if not combined:
                print("  [警告] 模型未返回有效内容，使用默认评估")
                evaluation = {"is_important": False, "is_relevant": False, "is_interested": False}
            else:
                result = None
                try:
                    result = json.loads(combined)
                except Exception:
                    start_idx = combined.rfind('{"is_important":')
                    if start_idx == -1:
                        start_idx = combined.find('"is_important":')
                    if start_idx != -1:
                        brace_start = combined.rfind('{', 0, start_idx + 1)
                        if brace_start != -1:
                            for end_idx in range(len(combined) - 1, brace_start, -1):
                                try:
                                    candidate = combined[brace_start:end_idx + 1]
                                    parsed = json.loads(candidate)
                                    if all(k in parsed for k in ("is_important", "is_relevant", "is_interested")):
                                        result = parsed
                                        break
                                except Exception:
                                    continue

                if result:
                    evaluation = {
                        "is_important": bool(result.get("is_important", False)),
                        "is_relevant": bool(result.get("is_relevant", False)),
                        "is_interested": bool(result.get("is_interested", False)),
                    }
                else:
                    print("  [警告] 无法从响应中解析 JSON，使用默认评估")
                    evaluation = {"is_important": False, "is_relevant": False, "is_interested": False}

        except Exception as e:
            print("  [警告] LLM 评估失败 '{}': {}, 使用默认评估".format(title[:30], str(e)[:50]))
            evaluation = {"is_important": False, "is_relevant": False, "is_interested": False}

        paper["evaluation"] = evaluation
        dl = should_download(evaluation)
        print("    评估结果: 重要={}, 相关={}, 有趣={} | 下载={}".format(
            evaluation["is_important"], evaluation["is_relevant"],
            evaluation["is_interested"], "是" if dl else "否"
        ))

    print("-" * 70)
    return papers


# ============================================================
# 步骤 7: 下载 PDF（按日期子目录 + 标题重命名）
# ============================================================
def download_papers_with_title_rename(papers: list[dict]):
    """
    下载论文 PDF 到日期子目录，并用论文标题重命名文件。
    文件命名格式: {arXiv_ID}_{论文标题}.pdf
    保存路径: {下载路径}/{日期}/papers/{arxiv_id}_{论文标题}.pdf
    """
    print("\n[步骤 3/7] 下载论文 PDF")
    print("-" * 70)

    today_str = date.today().strftime("%Y-%m-%d")
    save_dir = DOWNLOADS_DIR / today_str / "papers"
    save_dir.mkdir(parents=True, exist_ok=True)

    for i, paper in enumerate(papers):
        pdf_url = paper.get("pdf_url")
        arxiv_id = paper["arxiv_id"]
        safe_id = arxiv_id.replace("/", "_")
        title = paper["title"]

        if not pdf_url:
            print("  [{}/{}] [跳过] {} - 无 PDF 链接".format(i + 1, len(papers), title[:50]))
            paper["local_path"] = None
            paper["is_downloaded"] = False
            continue

        if not should_download(paper["evaluation"]):
            print("  [{}/{}] [跳过] {} - 未通过评估".format(i + 1, len(papers), title[:50]))
            paper["local_path"] = None
            paper["is_downloaded"] = False
            continue

        title_filename = _safe_filename(title, max_len=100)
        final_filename = "{}_{}.pdf".format(safe_id, title_filename)
        final_path = save_dir / final_filename

        if final_path.exists():
            print("  [{}/{}] [已存在] {}".format(i + 1, len(papers), final_filename))
            paper["local_path"] = str(final_path.relative_to(PROJECT_ROOT))
            paper["is_downloaded"] = True
            continue

        try:
            print("  [{}/{}] 正在下载: {}...".format(i + 1, len(papers), title[:50]), end="", flush=True)
            response = httpx.get(pdf_url, follow_redirects=True, timeout=120.0)
            response.raise_for_status()
            final_path.write_bytes(response.content)
            size_kb = len(response.content) / 1024
            print("\r  [{}/{}] [成功] {} ({:.1f} KB)".format(
                i + 1, len(papers), final_filename, size_kb
            ))
            paper["local_path"] = str(final_path.relative_to(PROJECT_ROOT))
            paper["is_downloaded"] = True
        except Exception as e:
            print("\r  [{}/{}] [失败] {}: {}".format(
                i + 1, len(papers), title[:50], str(e)[:40]
            ))
            paper["local_path"] = None
            paper["is_downloaded"] = False

    success_count = sum(1 for p in papers if p["is_downloaded"])
    print("-" * 70)
    print("下载完成: {}/{} 成功".format(success_count, len(papers)))
    return papers


# ============================================================
# 步骤 8: 引用估算 + 摘要关键词分析
# ============================================================
def analyze_papers(papers: list[dict]) -> list[dict]:
    """
    对每篇论文进行引用指标估算和摘要关键词分析。
    """
    print("\n[步骤 4/7] 引用估算 + 摘要关键词分析")
    print("-" * 70)

    citation_analyzer = CitationAnalyzer()
    stop_words = {
        'this', 'that', 'these', 'those', 'their', 'there', 'where',
        'which', 'what', 'when', 'with', 'from', 'have', 'been',
        'more', 'than', 'into', 'over', 'such', 'also', 'only',
        'other', 'some', 'them', 'then', 'well', 'very', 'each',
        'make', 'like', 'just', 'many', 'most', 'does', 'could',
        'would', 'should', 'between', 'through', 'after', 'about',
        'above', 'below', 'during', 'without', 'within', 'along',
        'both', 'around', 'show', 'shows', 'used', 'using', 'based',
        'model', 'models', 'paper', 'propose', 'proposed', 'method',
        'approach', 'results', 'result', 'study', 'studies', 'work',
        'performance', 'significant', 'significantly', 'state', 'art',
        'new', 'novel', 'large', 'language', 'llm', 'llms', 'one',
        'two', 'first', 'may', 'also', 'can', 'our', 'out', 'data',
    }

    for i, paper in enumerate(papers):
        print("  [{}/{}] {}".format(i + 1, len(papers), paper["title"][:60]))

        abstract_words = re.findall(r'\b[a-zA-Z]{4,}\b', paper["abstract"].lower())
        keywords = [w for w in abstract_words if w not in stop_words]
        keyword_freq = Counter(keywords).most_common(10)
        paper["top_keywords"] = [{"word": w, "freq": f} for w, f in keyword_freq]
        print("    关键词 Top10: {}".format(", ".join(w for w, _ in keyword_freq[:5])))

        try:
            p = Paper(
                id=paper["arxiv_id"],
                title=paper["title"],
                authors=paper["authors"],
                abstract=paper["abstract"],
                published=str(paper["published_date"]),
                categories=paper["categories"],
                arxiv_url=paper.get("source_url", ""),
                pdf_url=paper.get("pdf_url", ""),
            )
            ci = citation_analyzer.estimate_citations(p)
            paper["citation_info"] = {
                "estimated_citations": ci.estimated_citations,
                "citations_per_year": ci.citations_per_year,
                "h_index_contribution": ci.h_index_contribution,
            }
            print("    估算引用: {}, 年均: {}, H-index贡献: {}".format(
                ci.estimated_citations, ci.citations_per_year, ci.h_index_contribution
            ))
        except Exception as e:
            paper["citation_info"] = {"estimated_citations": 0, "citations_per_year": 0.0, "h_index_contribution": 0}
            print("    [警告] 引用估算失败: {}".format(str(e)[:40]))

    print("-" * 70)
    return papers


# ============================================================
# 步骤 9: 导出 JSON 报告（所有搜索论文，含未下载的）
# ============================================================
def export_json(all_papers: list[dict]):
    """
    将所有搜索论文的详细记录导出为 JSON 格式（含评估/引用/是否下载等完整信息）。
    保存路径: {下载路径}/{日期}/papers/daily_paper_search_detail.json
    """
    today_str = date.today().strftime("%Y-%m-%d")
    output_path = DOWNLOADS_DIR / today_str / "papers" / "daily_paper_search_detail.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("\n[步骤 5/7] 导出论文搜索记录 (JSON): {}".format(output_path))

    export_data = []
    for p in all_papers:
        export_data.append({
            "arxiv_id": p["arxiv_id"],
            "title": p["title"],
            "authors": p["authors"],
            "published_date": str(p["published_date"]),
            "categories": p["categories"],
            "abstract": p["abstract"],
            "arxiv_url": p.get("source_url", ""),
            "pdf_url": p.get("pdf_url", ""),
            "local_path": p.get("local_path", ""),
            "is_downloaded": p.get("is_downloaded", False),
            "evaluation": p.get("evaluation", {}),
            "top_keywords": p.get("top_keywords", []),
            "citation_info": p.get("citation_info", {}),
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    print("  已保存 {} 条记录（含未下载论文）".format(len(export_data)))
    return output_path


# ============================================================
# 步骤 10: 导出 Markdown 论文列表（仅下载的论文）
# ============================================================
def export_markdown(downloaded_papers: list[dict]):
    """
    将已下载论文的分析报告导出为 Markdown 格式。
    保存路径: {下载路径}/{日期}/papers/daily_paper_analysis.md
    """
    today_str = date.today().strftime("%Y-%m-%d")
    output_path = DOWNLOADS_DIR / today_str / "papers" / "daily_paper_analysis.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("\n[步骤 6/7] 导出论文分析报告 (Markdown): {}".format(output_path))

    lines = [
        "# arXiv 论文分析报告\n",
        "> 生成时间: {}  |  下载成功: {} 篇\n".format(
            today_str,
            len(downloaded_papers),
        ),
        "---\n",
    ]

    for i, p in enumerate(downloaded_papers, 1):
        eval_ = p.get("evaluation", {})
        imp = "Y" if eval_.get("is_important") else "N"
        rel = "Y" if eval_.get("is_relevant") else "N"
        int_ = "Y" if eval_.get("is_interested") else "N"

        lines.append("## {}. {}\n\n".format(i, p["title"]))
        lines.append("- **作者**: {}\n".format(", ".join(p["authors"][:3])))
        if len(p["authors"]) > 3:
            lines[-1] = lines[-1].rstrip("\n") + " 等\n"
        lines.append("- **arXiv ID**: [{arxiv_id}]({url})\n".format(
            arxiv_id=p["arxiv_id"], url=p.get("source_url", "#")
        ))
        lines.append("- **发布日期**: {}\n".format(p["published_date"]))
        lines.append("- **分类**: {}\n".format(", ".join(p["categories"][:5])))
        lines.append("- **评估**: 重要[{}] 相关[{}] 有趣[{}]\n".format(imp, rel, int_))

        keywords = p.get("top_keywords", [])
        if keywords:
            kw_str = ", ".join("{} ({})".format(k["word"], k["freq"]) for k in keywords[:8])
            lines.append("- **关键词**: {}\n".format(kw_str))

        if p.get("local_path"):
            lines.append("- **PDF**: [本地文件]({})\n".format(p["local_path"]))

        abstract = p["abstract"].replace("\n", " ").strip()
        if len(abstract) > 400:
            abstract = abstract[:400] + "..."
        lines.append("\n**摘要**: {}\n\n".format(abstract))

        cit = p.get("citation_info", {})
        lines.append("- **估算引用**: {}, **年均**: {}, **H-index贡献**: {}\n".format(
            cit.get("estimated_citations", "?"),
            cit.get("citations_per_year", "?"),
            cit.get("h_index_contribution", "?"),
        ))
        lines.append("---\n\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("  已保存 {} 篇已下载论文".format(len(downloaded_papers)))
    return output_path


# ============================================================
# 步骤 11: 打印总结报告
# ============================================================
def print_summary(all_papers: list[dict], downloaded_papers: list[dict]):
    """在控制台打印最终的总结报告"""
    print("\n" + "=" * 70)
    print("步骤 7/7: 执行总结")
    print("=" * 70)

    total = len(all_papers)
    downloaded = len(downloaded_papers)
    important = sum(1 for p in all_papers if p.get("evaluation", {}).get("is_important"))
    relevant = sum(1 for p in all_papers if p.get("evaluation", {}).get("is_relevant"))
    interested = sum(1 for p in all_papers if p.get("evaluation", {}).get("is_interested"))
    today_str = date.today().strftime("%Y-%m-%d")

    print("\n论文统计:")
    print("  总计: {} 篇".format(total))
    print("  重要: {} 篇".format(important))
    print("  相关: {} 篇".format(relevant))
    print("  有趣: {} 篇".format(interested))
    print("  下载成功: {} 篇".format(downloaded))

    print("\n已下载论文列表:")
    if downloaded_papers:
        for i, p in enumerate(downloaded_papers, 1):
            print("  {}. [{}] {}".format(i, p["arxiv_id"], p["title"][:60]))
    else:
        print("  (无)")

    papers_dir = DOWNLOADS_DIR / today_str / "papers"
    print("\n输出文件:")
    print("  - 搜索记录:   {}".format(papers_dir / "daily_paper_search_detail.json"))
    print("  - 分析报告:   {}".format(papers_dir / "daily_paper_analysis.md"))
    print("  - PDF 目录:   {}".format(papers_dir))


# ============================================================
# 主函数: 整合所有步骤
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="从 arXiv 下载论文并分析（支持本地 LLM 评估）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 指定单篇论文
  python test/demo_arxiv_pipeline.py --arxiv-id 2604.02331

  # 指定多篇论文
  python test/demo_arxiv_pipeline.py --arxiv-id 2604.02331,2503.21456

  # 关键词搜索
  python test/demo_arxiv_pipeline.py --search "large language model reasoning"

  # 搜索更多结果
  python test/demo_arxiv_pipeline.py --search "transformer" --max 10

  # 自定义 LLM 端点
  python test/demo_arxiv_pipeline.py --arxiv-id 2604.02331 \\
    --lm-url http://127.0.0.1:5001/v1 --lm-model local-model
        """,
    )
    parser.add_argument("--arxiv-id", type=str, default="",
                        help="arXiv ID（支持多个，逗号分隔，如 2604.02331,2503.21456）")
    parser.add_argument("--search", type=str, default="",
                        help="搜索关键词（与 --arxiv-id 互斥）")
    parser.add_argument("--max", dest="max_results", type=int, default=5,
                        help="搜索模式下的最大返回数量（默认 5）")
    parser.add_argument("--no-evaluate", action="store_true",
                        help="跳过 LLM 评估步骤")
    parser.add_argument("--lm-url", dest="lm_url", type=str, default="",
                        help="LM Studio API 地址（覆盖默认值）")
    parser.add_argument("--lm-model", dest="lm_model", type=str, default="",
                        help="LM Studio 模型名称（覆盖默认值）")

    args = parser.parse_args()

    global LM_STUDIO_BASE_URL, LM_STUDIO_MODEL
    if args.lm_url:
        LM_STUDIO_BASE_URL = args.lm_url
    if args.lm_model:
        LM_STUDIO_MODEL = args.lm_model

    print("=" * 70)
    print("arXiv 论文下载与分析 Pipeline")
    print("=" * 70)
    print("LM Studio 端点: {}".format(LM_STUDIO_BASE_URL))
    print("LM Studio 模型: {}".format(LM_STUDIO_MODEL))
    print("下载目录: {}".format(DOWNLOADS_DIR))
    print("=" * 70)

    papers = []

    if args.arxiv_id:
        arxiv_ids = [aid.strip() for aid in args.arxiv_id.split(",") if aid.strip()]
        for aid in arxiv_ids:
            p = fetch_paper_by_id(aid)
            if p:
                papers.append(p)

    elif args.search:
        papers = search_and_select(args.search, max_results=args.max_results)

    else:
        print("\n交互模式 - 请选择操作:")
        print("  1. 输入 arXiv ID（支持多个，逗号分隔）")
        print("  2. 输入搜索关键词（返回结果供选择）")
        print("  3. 退出")
        try:
            choice = input("\n请选择 (1/2/3): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("已退出")
            return

        if choice == "1":
            try:
                ids_input = input("arXiv ID(s): ").strip()
            except (EOFError, KeyboardInterrupt):
                return
            arxiv_ids = [aid.strip() for aid in ids_input.split(",") if aid.strip()]
            for aid in arxiv_ids:
                p = fetch_paper_by_id(aid)
                if p:
                    papers.append(p)

        elif choice == "2":
            try:
                keyword = input("搜索关键词: ").strip()
            except (EOFError, KeyboardInterrupt):
                return
            if keyword:
                papers = search_and_select(keyword, max_results=5)
        else:
            print("已退出")
            return

    if not papers:
        print("\n没有找到任何论文，退出。")
        return

    if not args.no_evaluate:
        papers = evaluate_with_lmstudio(papers)
    else:
        for p in papers:
            p["evaluation"] = {"is_important": False, "is_relevant": False, "is_interested": False}
        print("\n[跳过] LLM 评估步骤（--no-evaluate）")

    papers = download_papers_with_title_rename(papers)
    papers = analyze_papers(papers)

    today_str = date.today().strftime("%Y-%m-%d")
    json_path = export_json(papers)
    downloaded = [p for p in papers if p.get("is_downloaded")]
    md_path = export_markdown(downloaded) if downloaded else None
    print_summary(papers, downloaded)

    print("\n" + "=" * 70)
    print("Pipeline 执行完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
