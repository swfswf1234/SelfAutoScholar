"""SelfAutoScholar 主入口 - 完整链路

功能:
    1. 按关键词搜索 arXiv 论文
    2. 调用 LLM 评估论文重要性/相关性/兴趣度
    3. 根据评估结果下载 PDF
    4. 输出搜索记录 JSON + 已下载论文 Markdown 分析报告

使用方式:
    python -m app.main --no-db --keywords "large language model"
"""

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

from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.models.paper import Paper
from app.services.arxiv_client import search_by_keywords
from app.services.llm_service import LLMService, should_download
from app.services.pdf_downloader import download_papers
from app.services.llm_service import LLMService


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


def _export_json(all_papers: list[dict], output_path: Path):
    """导出所有搜索论文的详细记录为 JSON"""
    def _to_serializable(obj):
        if isinstance(obj, date):
            return obj.isoformat()
        return obj

    export_data = []
    for p in all_papers:
        export_data.append({k: _to_serializable(v) for k, v in p.items()})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)


def _export_markdown(downloaded_papers: list[dict], output_path: Path):
    """导出已下载论文的分析报告为 Markdown"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    today_str = date.today().strftime("%Y-%m-%d")

    lines = [
        "# arXiv 论文分析报告\n",
        "> 生成时间: {}  |  下载成功: {} 篇\n---\n".format(
            today_str, len(downloaded_papers)
        ),
    ]

    for i, p in enumerate(downloaded_papers, 1):
        ev = p.get("evaluation", {})
        lines.append("## {}. {}\n\n".format(i, p["title"]))
        lines.append("- **作者**: {}\n".format(", ".join(p["authors"][:3])))
        if len(p["authors"]) > 3:
            lines[-1] = lines[-1].rstrip("\n") + " 等\n"
        lines.append("- **arXiv ID**: [{id}]({url})\n".format(
            id=p["arxiv_id"], url=p.get("source_url", "#")
        ))
        lines.append("- **发布日期**: {}\n".format(p.get("published_date", "")))
        lines.append("- **评估**: 重要[{}] 相关[{}] 有趣[{}]\n".format(
            "Y" if ev.get("is_important") else "N",
            "Y" if ev.get("is_relevant") else "N",
            "Y" if ev.get("is_interested") else "N",
        ))
        if p.get("local_path"):
            lines.append("- **PDF**: [本地文件]({})\n".format(p["local_path"]))
        abstract = p.get("abstract", "").replace("\n", " ").strip()
        if len(abstract) > 400:
            abstract = abstract[:400] + "..."
        lines.append("\n**摘要**: {}\n\n---\n\n".format(abstract))

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def main():
    """主流程"""
    parser = argparse.ArgumentParser(description="SelfAutoScholar - arXiv 论文自动发现与下载")
    parser.add_argument("--no-db", action="store_true",
                        help="跳过数据库连接，以单机模式运行（仅搜索+评估+下载）")
    parser.add_argument("--keywords", type=str, default="",
                        help="搜索关键词（逗号分隔），覆盖配置文件")
    args = parser.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()] if args.keywords else settings.search_keywords
    today_str = date.today().strftime("%Y-%m-%d")
    papers_dir = settings.get_downloads_path() / today_str / "papers"

    print("=" * 60)
    print("  SelfAutoScholar 启动")
    print("=" * 60)
    print("  评估 Provider: {} ({})".format(settings.evaluation_provider, settings.local_llm_model))
    print("  搜索关键词: {}".format(keywords))
    print("  数据库模式: {}".format("跳过" if args.no_db else "启用"))
    print("  输出目录:   {}".format(papers_dir))
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
            return

        # ===== 3. LLM 评估 =====
        llm_service = LLMService()
        print("\n[3/7] LLM 评估")
        unique_papers = llm_service.evaluate_papers(unique_papers)

        # ===== 4. 下载决策 =====
        print("\n[4/7] 下载决策...")
        to_download = [p for p in unique_papers if should_download(p["evaluation"])]
        to_download = to_download[:settings.max_downloads]
        print("  决定下载: {} 篇".format(len(to_download)))

        if not to_download:
            print("  无符合条件的论文，退出")
            _export_json(all_papers, papers_dir / "daily_paper_search_detail.json")
            return

        # ===== 5. PDF 下载 =====
        print("\n[5/7] 下载 PDF...")
        downloaded_papers = download_papers(to_download, settings.get_downloads_path())

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

        # 7a. 所有搜索论文 JSON（含未下载）
        json_path = papers_dir / "daily_paper_search_detail.json"
        _export_json(all_papers, json_path)
        print("  搜索记录 (JSON): {}".format(json_path))

        # 7b. 已下载论文 Markdown 分析报告
        downloaded = [p for p in downloaded_papers if p.get("is_downloaded")]
        if downloaded:
            md_path = papers_dir / "daily_paper_analysis.md"
            _export_markdown(downloaded, md_path)
            print("  分析报告 (Markdown): {}".format(md_path))
        else:
            print("  分析报告: 无已下载论文，跳过 Markdown")

        print("\n  执行完成!")

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
