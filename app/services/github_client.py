"""GitHub 仓库搜索服务

功能:
    - 搜索开源项目仓库 (按关键词/语言/星标数)
    - 获取仓库详情 (stars, forks, topics, description)
    - 获取最新 release/commits
    - 仓库重要性评估

配置项 (setting.ini [GitHub] 节点):
    api_base     - GitHub API 地址 (默认 https://api.github.com)
    token        - GitHub Token (可选，用于增加 rate limit)
"""

import time
from typing import Any
from github import Github
import httpx

from app.core.config import settings


def _get_headers() -> dict:
    """构建请求头"""
    headers = {
        "Accept": "application/vnd.github.v3+json",
    }
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"
    return headers


def search_repositories(
    query: str,
    language: str | None = None,
    sort: str = "stars",
    order: str = "desc",
    max_results: int = 20,
) -> list[dict]:
    """
    搜索 GitHub 仓库

    Args:
        query: 搜索关键词
        language: 编程语言筛选 (如 python, javascript)
        sort: 排序方式 (stars, forks, updated)
        order: 排序顺序 (desc, asc)
        max_results: 最大返回数量

    Returns:
        仓库列表
    """
    q = query
    if language:
        q += f" language:{language}"

    params = {
        "q": q,
        "sort": sort,
        "order": order,
        "per_page": min(max_results, 100),
    }

    url = f"{settings.github_api_base}/search/repositories"

    for attempt in range(3):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, params=params, headers=_get_headers())
                response.raise_for_status()
                data = response.json()

                repos = []
                for item in data.get("items", [])[:max_results]:
                    repos.append({
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "full_name": item.get("full_name"),
                        "owner": item.get("owner", {}).get("login"),
                        "description": item.get("description"),
                        "html_url": item.get("html_url"),
                        "stars": item.get("stargazers_count", 0),
                        "forks": item.get("forks_count", 0),
                        "language": item.get("language"),
                        "topics": item.get("topics", []),
                        "license": item.get("license", {}).get("name"),
                        "created_at": item.get("created_at"),
                        "updated_at": item.get("updated_at"),
                        "pushed_at": item.get("pushed_at"),
                    })
                return repos

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                reset_time = e.response.headers.get("X-RateLimit-Reset")
                if reset_time:
                    wait_time = int(reset_time) - int(time.time()) + 1
                    if wait_time > 0:
                        print(f"  GitHub API rate limit, 等待 {wait_time} 秒...")
                        time.sleep(wait_time)
                        continue
            print(f"  GitHub 搜索失败: {e}")
            return []
        except Exception as e:
            print(f"  GitHub 搜索失败: {e}")
            return []

    return []


def get_repo_info(owner: str, repo: str) -> dict | None:
    """
    获取仓库详细信息

    Args:
        owner: 仓库所有者
        repo: 仓库名

    Returns:
        仓库详情 dict
    """
    url = f"{settings.github_api_base}/repos/{owner}/{repo}"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=_get_headers())
            response.raise_for_status()
            item = response.json()

            return {
                "id": item.get("id"),
                "name": item.get("name"),
                "full_name": item.get("full_name"),
                "owner": item.get("owner", {}).get("login"),
                "description": item.get("description"),
                "html_url": item.get("html_url"),
                "stars": item.get("stargazers_count", 0),
                "forks": item.get("forks_count", 0),
                "watchers": item.get("watchers_count", 0),
                "language": item.get("language"),
                "topics": item.get("topics", []),
                "license": item.get("license", {}).get("name"),
                "default_branch": item.get("default_branch"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "pushed_at": item.get("pushed_at"),
                "homepage": item.get("homepage"),
                "size": item.get("size"),
                "open_issues": item.get("open_issues_count"),
            }

    except Exception as e:
        print(f"  获取仓库信息失败: {e}")
        return None


def get_latest_release(owner: str, repo: str) -> dict | None:
    """
    获取仓库最新 Release

    Args:
        owner: 仓库所有者
        repo: 仓库名

    Returns:
        Release 信息
    """
    url = f"{settings.github_api_base}/repos/{owner}/{repo}/releases/latest"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=_get_headers())
            response.raise_for_status()
            item = response.json()

            return {
                "tag_name": item.get("tag_name"),
                "name": item.get("name"),
                "body": item.get("body"),
                "html_url": item.get("html_url"),
                "published_at": item.get("published_at"),
                "zipball_url": item.get("zipball_url"),
                "tarball_url": item.get("tarball_url"),
            }

    except Exception:
        return None


def get_repo_readme(owner: str, repo: str) -> str | None:
    """
    获取仓库 README 内容

    Args:
        owner: 仓库所有者
        repo: 仓库名

    Returns:
        README 文本
    """
    url = f"{settings.github_api_base}/repos/{owner}/{repo}/readme"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=_get_headers())
            response.raise_for_status()
            item = response.json()
            content = item.get("content", "")
            if content:
                import base64
                return base64.b64decode(content).decode("utf-8")
            return None

    except Exception:
        return None


def search_by_keywords(keywords: list[str], max_per_keyword: int = 10) -> list[dict]:
    """
    按多个关键词搜索并合并去重

    Args:
        keywords: 关键词列表
        max_per_keyword: 每个关键词最大返回数量

    Returns:
        去重后的仓库列表
    """
    all_repos = []
    seen_names = set()

    for i, keyword in enumerate(keywords):
        if i > 0:
            time.sleep(1)

        repos = search_repositories(keyword, max_results=max_per_keyword)
        new_count = 0
        for r in repos:
            if r["full_name"] not in seen_names:
                seen_names.add(r["full_name"])
                all_repos.append(r)
                new_count += 1
        print(f"  关键词 '{keyword}': 搜索 {len(repos)} 个, 新增 {new_count} 个")

    print(f"  总计: {len(all_repos)} 个去重后仓库")
    return all_repos
