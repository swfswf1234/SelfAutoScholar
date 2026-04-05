"""SelfAutoScholar 主入口 - Demo 完整链路"""

import sys
import io

# Windows 控制台 UTF-8 输出修复
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

import argparse
import json
import os
from datetime import date
from pathlib import Path

# 禁用 loguru 全局日志，避免 Windows 控制台编码问题
import loguru
loguru.logger.disable("loguru")

from openai import OpenAI

from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.models.paper import Paper
from app.services.arxiv_client import search_by_keywords
from app.services.llm_evaluator import evaluate_papers, should_download
from app.services.pdf_downloader import download_papers

LM_STUDIO_BASE_URL = os.environ.get("LM_STUDIO_BASE_URL", "http://127.0.0.1:5001/v1")
LM_STUDIO_API_KEY = "not-needed"
LM_STUDIO_MODEL = os.environ.get("LM_STUDIO_MODEL", "qwen/qwen3.5-9b")


def is_title_duplicate(db, title: str) -> bool:
    """检查标题是否已存在于数据库"""
    return db.query(Paper).filter(Paper.title == title).first() is not None


def dedup_papers(db, papers: list[dict]) -> list[dict]:
    """去重: 过滤已存在的论文"""
    unique_papers = []
    for p in papers:
        if not is_title_duplicate(db, p["title"]):
            unique_papers.append(p)
    return unique_papers


def save_to_db(db, paper: dict) -> Paper:
    """保存论文到数据库"""
    db_paper = Paper(
        arxiv_id=paper["arxiv_id"],
        title=paper["title"],
        abstract=paper["abstract"],
        authors=paper.get("authors", []),
        categories=paper.get("categories", []),
        source_url=paper.get("source_url"),
        pdf_url=paper.get("pdf_url"),
        local_path=paper.get("local_path"),
        is_important=paper["evaluation"]["is_important"],
        is_relevant=paper["evaluation"]["is_relevant"],
        is_interested=paper["evaluation"]["is_interested"],
        is_downloaded=paper.get("is_downloaded", False),
        published_date=paper.get("published_date"),
    )
    db.add(db_paper)
    return db_paper


def print_report(all_papers: list[dict], downloaded_papers: list[dict]):
    """打印报告"""
    today = date.today().strftime("%Y-%m-%d")

    print("\n" + "=" * 60)
    print("  SelfAutoScholar 每日报告 ({})".format(today))
    print("=" * 60)

    print("\n[统计]")
    print("  搜索论文总数: {} 篇".format(len(all_papers)))
    print("  评估通过: {} 篇".format(len(downloaded_papers)))

    if downloaded_papers:
        print("\n[已下载论文]")
        for i, p in enumerate(downloaded_papers, 1):
            ev = p["evaluation"]
            status = "重要{} 相关{} 感兴趣{}".format(
                "Y" if ev['is_important'] else "N",
                "Y" if ev['is_relevant'] else "N",
                "Y" if ev['is_interested'] else "N"
            )
            print("  {}. [{}] {}...".format(i, p['arxiv_id'], p['title'][:60]))
            print("     评估: {}".format(status))
            if p.get("local_path"):
                print("     路径: {}".format(p['local_path']))
    else:
        print("\n  (无符合条件的论文)")

    print("\n" + "=" * 60)


def _eval_single_paper(client: OpenAI, model: str, paper: dict) -> dict:
    """直接调用 LM Studio 评估单篇论文（处理 reasoning_content）"""
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
        response = client.chat.completions.create(
            model=model,
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

        result = None
        if combined:
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
            paper["evaluation"] = {
                "is_important": bool(result.get("is_important", False)),
                "is_relevant": bool(result.get("is_relevant", False)),
                "is_interested": bool(result.get("is_interested", False)),
            }
        else:
            paper["evaluation"] = {"is_important": False, "is_relevant": False, "is_interested": False}

    except Exception as e:
        paper["evaluation"] = {"is_important": False, "is_relevant": False, "is_interested": False}
    return paper


def _eval_with_lmstudio(papers: list[dict]) -> list[dict]:
    """使用 LM Studio 批量评估论文"""
    client = OpenAI(base_url=LM_STUDIO_BASE_URL, api_key=LM_STUDIO_API_KEY, timeout=120.0)
    print("\n[3/7] LLM 评估 (LM Studio: {})".format(LM_STUDIO_BASE_URL))
    for i, paper in enumerate(papers):
        print("  评估 [{}/{}]: {}...".format(i + 1, len(papers), paper["title"][:50]))
        paper = _eval_single_paper(client, LM_STUDIO_MODEL, paper)
        ev = paper["evaluation"]
        dl = should_download(ev)
        print("    -> 重要={}, 相关={}, 有趣={} | 下载={}".format(
            ev["is_important"], ev["is_relevant"], ev["is_interested"],
            "是" if dl else "否"
        ))
    return papers


def main():
    """主流程"""
    parser = argparse.ArgumentParser(description="SelfAutoScholar - arXiv 论文自动发现与下载")
    parser.add_argument("--no-db", action="store_true",
                        help="跳过数据库连接，以单机模式运行（仅搜索+评估+下载）")
    parser.add_argument("--keywords", type=str, default="",
                        help="搜索关键词（逗号分隔），覆盖配置文件")
    args = parser.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()] if args.keywords else settings.search_keywords

    print("=" * 60)
    print("  SelfAutoScholar Demo 启动")
    print("=" * 60)
    print("  LLM: {} ({})".format(LM_STUDIO_BASE_URL, LM_STUDIO_MODEL))
    print("  搜索关键词: {}".format(keywords))
    print("  数据库模式: {}".format("跳过" if args.no_db else "启用"))
    print("=" * 60)

    db = None
    if not args.no_db:
        try:
            print("\n[初始化] 连接数据库...")
            init_db()
            db = SessionLocal()
            print("  数据库连接成功")
        except Exception as e:
            print("  [警告] 数据库连接失败: {}，自动切换到无数据库模式".format(str(e)[:60]))
            print("  使用 --no-db 可显式跳过数据库")
            db = None

    try:
        # ===== 1. 搜索论文 =====
        print("\n[1/7] 搜索论文, 关键词: {}".format(keywords))
        all_papers = search_by_keywords(keywords, max_per_keyword=settings.max_candidates)
        print("  搜索到 {} 篇论文".format(len(all_papers)))

        # ===== 2. 去重检查 =====
        print("\n[2/7] 去重检查...")
        if db:
            unique_papers = dedup_papers(db, all_papers)
        else:
            unique_papers = all_papers
        print("  去重后: {} 篇".format(len(unique_papers)))

        if not unique_papers:
            print("  无新论文，退出")
            print_report(all_papers, [])
            return

        # ===== 3. LLM 评估 =====
        evaluated_papers = _eval_with_lmstudio(unique_papers)

        # ===== 4. 下载决策 =====
        print("\n[4/7] 下载决策...")
        to_download = [p for p in evaluated_papers if should_download(p["evaluation"])]
        to_download = to_download[:settings.max_downloads]
        print("  决定下载: {} 篇".format(len(to_download)))

        if not to_download:
            print("  无符合条件的论文，退出")
            print_report(all_papers, [])
            return

        # ===== 5. PDF 下载 =====
        print("\n[5/7] 下载 PDF...")
        downloads_path = settings.get_downloads_path()
        downloaded_papers = download_papers(to_download, downloads_path)

        # ===== 6. 入库保存 =====
        if db:
            print("\n[6/7] 入库保存...")
            for paper in downloaded_papers:
                if paper.get("is_downloaded"):
                    save_to_db(db, paper)
            db.commit()
            print("  数据库提交完成")
        else:
            print("\n[6/7] 跳过（无数据库）")

        # ===== 7. 输出报告 =====
        print("\n[7/7] 生成报告...")
        print_report(all_papers, downloaded_papers)

        # 导出 JSON 报告（处理 date 对象序列化）
        json_path = Path("data") / "app_papers.json"
        json_path.parent.mkdir(exist_ok=True)

        def _to_serializable(obj):
            if isinstance(obj, date):
                return obj.isoformat()
            return obj

        json_data = []
        for p in downloaded_papers:
            json_data.append({k: _to_serializable(v) for k, v in p.items()})
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        print("  JSON 报告已保存: {}".format(json_path))

        print("\n  Demo 执行完成!")

    except Exception as e:
        print("\n  [错误] 执行出错: {}".format(str(e)))
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()


if __name__ == "__main__":
    main()
