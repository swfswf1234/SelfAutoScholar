"""TextbookHunter — 教材 PDF 检索

用法:
    from app.collectors.textbook_hunter import TextbookHunter
    hunter = TextbookHunter()
    hunter.interactive_search("Munkres Topology")  # 交互式搜索
"""

import re
import httpx
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from bs4 import BeautifulSoup
from loguru import logger

from app.collectors import BaseCollector, ResourceInfo
from app.core.config import settings


TEXTBOOK_TARGETS = {
    "03_topology":     {"en": "Munkres Topology", "zh": "点集拓扑学 熊金城"},
    "04_real_analysis": {"en": "Stein Real Analysis; Folland Real Analysis", "zh": "实变函数 周民强"},
    "05_complex_analysis": {"en": "Stein Complex Analysis; Ahlfors Complex Analysis", "zh": ""},
    "06_functional_analysis": {"en": "Stein Functional Analysis; Lax Functional Analysis", "zh": "泛函分析 张恭庆"},
    "07_ode":          {"en": "Tenenbaum Ordinary Differential Equations", "zh": "常微分方程 丁同仁"},
    "08_pde":          {"en": "Evans Partial Differential Equations", "zh": ""},
    "09_abstract_algebra": {"en": "Dummit Abstract Algebra; Aluffi Algebra Chapter 0", "zh": ""},
    "10_qe_prep":      {"en": "Berkeley Problems in Mathematics", "zh": ""},
}


class LibGenHunter:
    """Library Genesis 搜索器"""

    BASE_URL = "https://libgen.is"
    SEARCH_URL = f"{BASE_URL}/search.php"

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout, follow_redirects=True)

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        params = {
            "req": query,
            "lg_topic": "libgen",
            "open": 0,
            "view": "simple",
            "res": max_results,
            "phrase": 1,
            "column": "def",
        }
        try:
            resp = self.client.get(self.SEARCH_URL, params=params)
            resp.raise_for_status()
            return self._parse_results(resp.text)
        except Exception as e:
            logger.warning(f"LibGen 搜索失败 '{query}': {e}")
            return []

    def _parse_results(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", class_="c")
        if not table:
            return []

        results = []
        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 10:
                continue
            try:
                title_td = cols[2]
                title_link = title_td.find("a")
                title = title_link.get_text(strip=True) if title_link else title_td.get_text(strip=True)
                author = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                year = cols[4].get_text(strip=True) if len(cols) > 4 else ""
                lang = cols[6].get_text(strip=True) if len(cols) > 6 else ""
                size = cols[7].get_text(strip=True) if len(cols) > 7 else ""
                ext = cols[8].get_text(strip=True) if len(cols) > 8 else ""

                dl_links = cols[9].find_all("a") if len(cols) > 9 else []
                download_url = ""
                for a in dl_links:
                    href = a.get("href", "")
                    if href.startswith("http"):
                        download_url = href
                        break
                if not download_url and dl_links:
                    download_url = dl_links[0].get("href", "")

                if ext.lower() != "pdf":
                    continue

                results.append({
                    "title": title,
                    "author": author,
                    "year": year,
                    "language": lang,
                    "size": size,
                    "download_url": download_url,
                })
            except Exception:
                continue

        return results

    def download(self, url: str, save_path: Path) -> bool:
        try:
            resp = self.client.get(url, follow_redirects=True, timeout=120.0)
            resp.raise_for_status()

            actual_url = str(resp.url)
            if "library.lol" in actual_url or actual_url.endswith(".pdf"):
                pdf_resp = self.client.get(actual_url, follow_redirects=True, timeout=120.0)
                pdf_resp.raise_for_status()
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_path.write_bytes(pdf_resp.content)
                return True
            return False
        except Exception as e:
            logger.error(f"下载失败: {e}")
            return False

    def close(self):
        self.client.close()


class TextbookHunter(BaseCollector):
    source = "textbook"

    def __init__(self):
        self.hunter = LibGenHunter()

    def search_course(self, course: str, query: str) -> list[dict]:
        print(f"\n检索: {course} -> {query}")
        return self.hunter.search(query, max_results=8)

    def interactive_search(self, course: str, query: str):
        results = self.search_course(course, query)
        save_dir = settings.dataset_path / "textbooks" / course
        downloaded = []

        if not results:
            print("  [无结果]")
            return downloaded

        print(f"  找到 {len(results)} 个结果:")
        for i, r in enumerate(results, 1):
            print(f"  [{i}] {r['title'][:70]}")
            print(f"      作者: {r['author']} | {r['year']} | {r['size']} | {r['language']}")

        while True:
            try:
                choice = input("  选择下载 [1-{0}/skip]: ".format(len(results))).strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = "skip"
            if choice == "skip":
                break
            if choice.isdigit() and 1 <= int(choice) <= len(results):
                idx = int(choice) - 1
                r = results[idx]
                safe_title = re.sub(r'[<>:"/\\|?*]', "", r["title"]).strip()[:80]
                safe_title = re.sub(r'\s+', "_", safe_title)
                filename = f"{safe_title}.pdf"
                filepath = save_dir / filename

                print(f"    下载中: {r['download_url'][:60]}...")
                ok = self.hunter.download(r["download_url"], filepath)
                if ok:
                    rel = filepath.relative_to(settings.dataset_path)
                    print(f"    ✓ 已保存: {rel}")
                    downloaded.append({**r, "local_path": str(rel.as_posix()), "course": course})
                else:
                    print(f"    ✗ 下载失败")
                break

        return downloaded

    def interactive_all(self):
        for course, targets in TEXTBOOK_TARGETS.items():
            en_query = targets.get("en", "")
            zh_query = targets.get("zh", "")
            all_downloaded = []

            if zh_query:
                print(f"\n{'='*60}")
                print(f"课程: {course} (中文)")
                print(f"{'='*60}")
                all_downloaded.extend(self.interactive_search(course, zh_query))

            if en_query:
                for q in en_query.split(";"):
                    q = q.strip()
                    if not q:
                        continue
                    print(f"\n{'='*60}")
                    print(f"课程: {course} (英文: {q})")
                    print(f"{'='*60}")
                    all_downloaded.extend(self.interactive_search(course, q))

            if not zh_query and not en_query:
                print(f"\n{'='*60}")
                print(f"课程: {course} (无目标)")
                print(f"{'='*60}")

        self.hunter.close()
