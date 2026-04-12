"""统一去重服务

功能:
    - 论文: 标题精确匹配去重
    - 项目: GitHub ID (owner/repo) 精确匹配去重
    
Usage:
    from app.services.dedup import DedupService, dedup_papers, dedup_projects
    
    service = DedupService()
    unique_papers = service.dedup_papers(papers)
    unique_projects = service.dedup_projects(projects)
"""

from typing import Any


class DedupService:
    """去重服务"""
    
    def __init__(self):
        self._paper_titles = set()
        self._project_ids = set()
    
    def reset(self):
        """重置去重状态"""
        self._paper_titles.clear()
        self._project_ids.clear()
    
    def dedup_papers(self, papers: list[dict]) -> list[dict]:
        """
        对论文列表去重 (标题精确匹配)
        
        Args:
            papers: 论文列表, 每项需含 title 字段
            
        Returns:
            去重后的论文列表
        """
        unique = []
        for p in papers:
            title = p.get("title", "").strip()
            if title and title not in self._paper_titles:
                self._paper_titles.add(title)
                unique.append(p)
        return unique
    
    def dedup_projects(self, projects: list[dict]) -> list[dict]:
        """
        对项目列表去重 (GitHub ID 精确匹配)
        
        Args:
            projects: 项目列表, 每项需含 full_name 字段 (owner/repo)
            
        Returns:
            去重后的项目列表
        """
        unique = []
        for p in projects:
            github_id = p.get("full_name", "").strip()
            if github_id and github_id not in self._project_ids:
                self._project_ids.add(github_id)
                unique.append(p)
        return unique
    
    def dedup_all(self, papers: list[dict] = None, projects: list[dict] = None) -> tuple[list[dict], list[dict]]:
        """
        对论文和项目列表统一去重
        
        Args:
            papers: 论文列表
            projects: 项目列表
            
        Returns:
            (去重后的论文列表, 去重后的项目列表)
        """
        unique_papers = self.dedup_papers(papers or [])
        unique_projects = self.dedup_projects(projects or [])
        return unique_papers, unique_projects


def dedup_papers(papers: list[dict]) -> list[dict]:
    """便捷函数: 对论文列表去重"""
    service = DedupService()
    return service.dedup_papers(papers)


def dedup_projects(projects: list[dict]) -> list[dict]:
    """便捷函数: 对项目列表去重"""
    service = DedupService()
    return service.dedup_projects(projects)