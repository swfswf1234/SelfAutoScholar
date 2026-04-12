"""Hacker News API 客户端"""

import httpx


def search_hackernews(query: str, max_results: int = 20) -> list[dict]:
    """
    搜索 Hacker News
    
    使用 HN Search API: https://hn.algolia.com/api/v1/search

    Args:
        query: 搜索关键词
        max_results: 最大返回数量

    Returns:
        新闻列表
    """
    url = "https://hn.algolia.com/api/v1/search"
    params = {
        "query": query,
        "tags": "story",
        "hitsPerPage": min(max_results, 100),
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("hits", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("url", f"https://news.ycombinator.com/item?id={item.get('objectID')}"),
                    "summary": item.get("story_text", "")[:500],
                    "pub_date": item.get("created_at", ""),
                    "source": "Hacker News",
                    "author": item.get("author", ""),
                    "points": item.get("points", 0),
                    "comments": item.get("num_comments", 0),
                })
            return results

    except Exception as e:
        print(f"  Hacker News 搜索失败: {e}")
        return []
