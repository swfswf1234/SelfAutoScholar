"""DocScraper — official documentation mirror (wget --mirror via WSL)"""

from app.collectors import BaseCollector
from app.core.config import settings
from app.tools.wget_mirror import WgetMirror


DOC_SOURCES = {
    "pytorch": ("https://docs.pytorch.org/docs/2.12/", 0.5),
    "scikit_learn": ("https://scikit-learn.org/stable/", 2),
    "xgboost": ("https://xgboost.readthedocs.io/en/stable/", 2),
    "yolo": ("https://docs.ultralytics.com/", 1),
}
"""Each entry: name -> (url, wait_seconds). wait controls wget --wait=N (lower = faster)."""


class DocScraper(BaseCollector):
    source = "official_docs"

    def __init__(self, proxy: str = ""):
        self.mirror = WgetMirror(proxy=proxy)

    def scrape(self, name: str, url: str, wait: float = 2.0) -> dict:
        save_dir = settings.dataset_path / "official_docs" / name
        return self.mirror.mirror(name, url, save_dir, wait=wait)

    def scrape_all(self) -> list[dict]:
        results = []
        for name, (url, wait) in DOC_SOURCES.items():
            r = self.scrape(name, url, wait=wait)
            results.append(r)
        return results
