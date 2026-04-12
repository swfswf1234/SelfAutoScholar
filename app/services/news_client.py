"""科技新闻搜索服务

功能:
    - 搜索科技新闻 (Hacker News, TechCrunch, 知乎)
    - RSS 订阅源抓取
    - 新闻详情获取

配置项 (setting.ini [News] 节点):
    rss_feeds    - RSS 订阅源列表 (逗号分隔)
"""

import re
import time
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings


DEFAULT_RSS_FEEDS = [
    "https://news.ycombinator.com/rss",
    "https://www.techcrunch.com/feed/",
    "https://www.zhihu.com/rss",
]


def _parse_rss_item(item: dict) -> dict:
    """解析 RSS 项为统一格式"""
    title = item.get("title", "")
    link = item.get("link", "")
    description = item.get("description", "")
    pub_date = item.get("published", "")

    soup = BeautifulSoup(description, "html.parser")
    summary = soup.get_text().strip()[:500]
    if len(description) > 500:
        summary += "..."

    return {
        "title": title,
        "link": link,
        "summary": summary,
        "pub_date": pub_date,
        "source": "",
    }


def fetch_rss_feed(feed_url: str, max_items: int = 20) -> list[dict]:
    """
    获取单个 RSS 源的文章列表

    Args:
        feed_url: RSS 链接
        max_items: 最大返回数量

    Returns:
        新闻列表
    """
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(feed_url)
            response.raise_for_status()
            text = response.text

        soup = BeautifulSoup(text, "xml")
        channel_title = soup.find("channel").find("title").get_text() if soup.find("channel") else feed_url

        items = soup.find_all("item")[:max_items]
        results = []
        for item in items:
            title = item.find("title").get_text() if item.find("title") else ""
            link = item.find("link").get_text() if item.find("link") else ""
            description = item.find("description").get_text() if item.find("description") else ""
            pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""

            soup_desc = BeautifulSoup(description, "html.parser")
            summary = soup_desc.get_text().strip()[:500]
            if len(description) > 500:
                summary += "..."

            results.append({
                "title": title,
                "link": link,
                "summary": summary,
                "pub_date": pub_date,
                "source": channel_title,
            })

        return results

    except Exception as e:
        print(f"  RSS 源获取失败 {feed_url}: {e}")
        return []


def fetch_rss_feeds(feed_urls: list[str] | None = None, max_per_feed: int = 10) -> list[dict]:
    """
    获取多个 RSS 源的文章

    Args:
        feed_urls: RSS 链接列表 (None 使用默认)
        max_per_feed: 每个源最大返回数量

    Returns:
        所有新闻列表
    """
    if feed_urls is None:
        feed_urls = settings.news_rss_feeds or DEFAULT_RSS_FEEDS

    all_news = []
    for url in feed_urls:
        news = fetch_rss_feed(url, max_per_feed)
        all_news.extend(news)
        time.sleep(0.5)

    all_news.sort(key=lambda x: x["pub_date"], reverse=True)
    return all_news


def search_hackernews(query: str, max_results: int = 20) -> list[dict]:
    """
    搜索 Hacker News

    Args:
        query: 搜索关键词
        max_results: 最大返回数量

    Returns:
        新闻列表
    """
    from app.services.hackernews_client import search_hackernews as hn_search
    return hn_search(query, max_results)


def search_zhihu(keyword: str, max_results: int = 10) -> list[dict]:
    """
    搜索知乎

    Args:
        keyword: 搜索关键词
        max_results: 最大返回数量

    Returns:
        知乎文章列表
    """
    url = "https://www.zhihu.com/api/v4/search_v3"

    params = {
        "q": keyword,
        "type": "article",
        "limit": max_results,
        "offset": 0,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("data", [])[:max_results]:
                info = item.get("object", {})
                results.append({
                    "title": info.get("title", ""),
                    "link": f"https://zhuanlan.zhihu.com/p/{info.get('id', '')}",
                    "summary": info.get("excerpt", "")[:500],
                    "pub_date": info.get("created_at", ""),
                    "source": "知乎",
                    "author": info.get("author", {}).get("name", ""),
                })
            return results

    except Exception as e:
        print(f"  知乎搜索失败: {e}")
        return []


def search_tech_news(
    keywords: list[str] | None = None,
    max_per_source: int = 10,
    sources: list[str] | None = None,
) -> list[dict]:
    """
    搜索科技新闻

    Args:
        keywords: 关键词列表 (用于知乎搜索)
        max_per_source: 每个源最大返回数量
        sources: 要搜索的源 (["hackernews", "zhihu", "rss"])

    Returns:
        合并后的新闻列表
    """
    if sources is None:
        sources = ["hackernews", "zhihu", "rss"]

    all_news = []

    if "rss" in sources:
        rss_news = fetch_rss_feeds(max_per_feed=max_per_source)
        all_news.extend(rss_news)

    if "hackernews" in sources:
        if keywords:
            for kw in keywords:
                hn_news = search_hackernews(kw, max_per_source)
                all_news.extend(hn_news)
        else:
            hn_news = fetch_rss_feed("https://news.ycombinator.com/rss", max_per_source)
            for n in hn_news:
                n["source"] = "Hacker News"
            all_news.extend(hn_news)

    if "zhihu" in sources and keywords:
        for kw in keywords:
            zh_news = search_zhihu(kw, max_per_source)
            all_news.extend(zh_news)
            time.sleep(0.5)

    return all_news


def get_news_detail(url: str) -> dict | None:
    """
    获取新闻详情

    Args:
        url: 新闻链接

    Returns:
        详情 dict
    """
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            title = soup.title.string if soup.title else ""
            description = ""
            meta_desc = soup.find("meta", {"name": "description"})
            if meta_desc:
                description = meta_desc.get("content", "")

            return {
                "url": url,
                "title": title,
                "description": description[:500],
                "fetched_at": datetime.now().isoformat(),
            }

    except Exception as e:
        print(f"  获取新闻详情失败: {e}")
        return None
