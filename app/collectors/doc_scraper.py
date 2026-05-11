"""DocScraper — 官方文档爬取 (wget --mirror)

用法:
    from app.collectors.doc_scraper import DocScraper
    scraper = DocScraper()
    scraper.scrape("pytorch", "https://pytorch.org/docs/stable/")
"""

import subprocess
import time
from pathlib import Path

from loguru import logger

from app.collectors import BaseCollector, ResourceInfo
from app.core.config import settings


DOC_SOURCES = {
    "pytorch": "https://pytorch.org/docs/stable/",
    "scikit_learn": "https://scikit-learn.org/stable/",
    "yolo": "https://docs.ultralytics.com/",
}


class DocScraper(BaseCollector):
    source = "official_docs"

    def scrape(self, name: str, url: str) -> dict:
        save_dir = settings.dataset_path / "official_docs" / name
        save_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"文档爬取: {name} <- {url}")
        logger.info(f"输出目录: {save_dir}")

        cmd = [
            "wget",
            "--mirror",
            "--convert-links",
            "--page-requisites",
            "--no-parent",
            "--directory-prefix", str(save_dir),
            "--wait", "2",
            "--random-wait",
            "--limit-rate", "500k",
            "--user-agent", "Mozilla/5.0",
            "--timeout", "30",
            "--tries", "3",
            url,
        ]

        logger.info(f"执行: {' '.join(cmd)}")
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.time() - start

        if result.returncode != 0:
            logger.warning(f"wget 返回非零: {result.returncode}")
            logger.debug(f"stderr: {result.stderr[:500]}")

        file_count = sum(1 for _ in save_dir.rglob("*") if _.is_file())
        page_count = sum(1 for _ in save_dir.rglob("*.html"))

        logger.info(f"完成: {name} — {file_count} 文件, {page_count} 页面, {elapsed:.0f}s")

        return {
            "name": name,
            "url": url,
            "local_path": str(save_dir.relative_to(settings.dataset_path).as_posix()),
            "file_count": file_count,
            "page_count": page_count,
            "elapsed_seconds": int(elapsed),
        }

    def scrape_all(self) -> list[dict]:
        results = []
        for name, url in DOC_SOURCES.items():
            r = self.scrape(name, url)
            results.append(r)
        return results
