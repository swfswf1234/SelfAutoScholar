"""PDF 下载服务"""

import httpx
from pathlib import Path
from datetime import date

from loguru import logger


def download_pdf(pdf_url: str, downloads_dir: Path, arxiv_id: str) -> str | None:
    """
    下载 PDF 文件

    Args:
        pdf_url: PDF 下载链接
        downloads_dir: 下载根目录
        arxiv_id: arXiv ID (用于命名)

    Returns:
        本地文件相对路径, 下载失败返回 None
    """
    # 创建日期目录
    today = date.today().strftime("%Y-%m-%d")
    save_dir = downloads_dir / today / "papers"
    save_dir.mkdir(parents=True, exist_ok=True)

    # 文件名 (替换 arXiv ID 中的 / 为 _)
    safe_id = arxiv_id.replace("/", "_")
    filename = f"{safe_id}.pdf"
    file_path = save_dir / filename

    # 如果已存在则跳过
    if file_path.exists():
        logger.info(f"文件已存在, 跳过: {filename}")
        return str(file_path.relative_to(downloads_dir.parent))

    try:
        logger.info(f"开始下载: {pdf_url}")
        response = httpx.get(pdf_url, follow_redirects=True, timeout=60.0)
        response.raise_for_status()

        file_path.write_bytes(response.content)
        file_size_kb = len(response.content) / 1024
        logger.info(f"下载完成: {filename} ({file_size_kb:.1f} KB)")

        # 返回相对于项目根目录的路径
        return str(file_path.relative_to(downloads_dir.parent))

    except Exception as e:
        logger.error(f"下载失败: {pdf_url} | 错误: {e}")
        return None


def download_papers(papers: list[dict], downloads_dir: Path) -> list[dict]:
    """
    批量下载论文 PDF

    Args:
        papers: 论文列表 (需含 pdf_url, arxiv_id)
        downloads_dir: 下载根目录

    Returns:
        添加了 local_path 字段的论文列表
    """
    logger.info(f"开始下载 {len(papers)} 篇论文")

    for i, paper in enumerate(papers):
        local_path = download_pdf(paper["pdf_url"], downloads_dir, paper["arxiv_id"])
        paper["local_path"] = local_path
        paper["is_downloaded"] = local_path is not None
        logger.debug(f"[{i+1}/{len(papers)}] {paper['arxiv_id']}")

    success = sum(1 for p in papers if p["is_downloaded"])
    logger.info(f"下载完成: {success}/{len(papers)} 成功")
    return papers
