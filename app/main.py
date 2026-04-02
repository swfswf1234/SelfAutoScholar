"""SelfAutoScholar 主入口 - Demo 完整链路"""

from datetime import date

from loguru import logger
from openai import OpenAI

from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.models.paper import Paper
from app.services.arxiv_client import search_by_keywords
from app.services.llm_evaluator import evaluate_papers, should_download
from app.services.pdf_downloader import download_papers


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
    print(f"  SelfAutoScholar 每日报告 ({today})")
    print("=" * 60)

    print(f"\n[统计]")
    print(f"  搜索论文总数: {len(all_papers)} 篇")
    print(f"  评估通过: {len(downloaded_papers)} 篇")

    if downloaded_papers:
        print(f"\n[已下载论文]")
        for i, p in enumerate(downloaded_papers, 1):
            ev = p["evaluation"]
            status = f"重要{'✓' if ev['is_important'] else '✗'} " \
                     f"相关{'✓' if ev['is_relevant'] else '✗'} " \
                     f"感兴趣{'✓' if ev['is_interested'] else '✗'}"
            print(f"  {i}. [{p['arxiv_id']}] {p['title'][:60]}...")
            print(f"     评估: {status}")
            if p.get("local_path"):
                print(f"     路径: {p['local_path']}")
    else:
        print("\n  (无符合条件的论文)")

    print("\n" + "=" * 60)


def main():
    """主流程"""
    logger.info("=" * 40)
    logger.info("SelfAutoScholar Demo 启动")
    logger.info("=" * 40)

    # 初始化数据库
    logger.info("初始化数据库...")
    init_db()
    db = SessionLocal()

    try:
        # ===== 1. 搜索论文 =====
        logger.info(f"[1/7] 搜索论文, 关键词: {settings.search_keywords}")
        all_papers = search_by_keywords(
            settings.search_keywords,
            max_per_keyword=settings.max_candidates
        )
        logger.info(f"  搜索到 {len(all_papers)} 篇论文")

        # ===== 2. 去重检查 =====
        logger.info("[2/7] 数据库去重检查...")
        unique_papers = dedup_papers(db, all_papers)
        logger.info(f"  去重后: {len(unique_papers)} 篇")

        if not unique_papers:
            logger.info("无新论文, 退出")
            print_report(all_papers, [])
            return

        # ===== 3. LLM 评估 =====
        logger.info("[3/7] LLM 评估...")
        llm_client = OpenAI(
            base_url=settings.llm_api_base,
            api_key=settings.llm_api_key,
        )
        evaluated_papers = evaluate_papers(
            llm_client, settings.llm_model, unique_papers
        )

        # ===== 4. 下载决策 =====
        logger.info("[4/7] 下载决策...")
        to_download = [p for p in evaluated_papers if should_download(p["evaluation"])]
        to_download = to_download[: settings.max_downloads]
        logger.info(f"  决定下载: {len(to_download)} 篇")

        if not to_download:
            logger.info("无符合条件的论文, 退出")
            print_report(all_papers, [])
            return

        # ===== 5. PDF 下载 =====
        logger.info("[5/7] 下载 PDF...")
        downloads_path = settings.get_downloads_path()
        downloaded_papers = download_papers(to_download, downloads_path)

        # ===== 6. 入库保存 =====
        logger.info("[6/7] 入库保存...")
        for paper in downloaded_papers:
            if paper.get("is_downloaded"):
                save_to_db(db, paper)
        db.commit()
        logger.info("  数据库提交完成")

        # ===== 7. 输出报告 =====
        logger.info("[7/7] 生成报告...")
        print_report(all_papers, downloaded_papers)

        logger.info("Demo 执行完成!")

    except Exception as e:
        logger.error(f"执行出错: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
