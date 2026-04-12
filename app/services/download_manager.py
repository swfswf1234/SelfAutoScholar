"""统一下载管理服务

功能:
    - 论文 PDF 下载
    - 项目 README 下载
    - 统一文件存储结构
    
Usage:
    from app.services.download_manager import DownloadManager
    
    manager = DownloadManager(base_path)
    papers = manager.download_papers(papers)
    projects = manager.download_projects(projects)
"""

import re
import httpx
from pathlib import Path
from datetime import date

from loguru import logger


class DownloadManager:
    """下载管理器"""
    
    def __init__(self, base_path: Path):
        """
        初始化下载管理器
        
        Args:
            base_path: 下载根目录 (项目根目录)
        """
        self.base_path = base_path
        self.today = date.today().strftime("%Y-%m-%d")
    
    def _safe_filename(self, name: str, max_len: int = 80) -> str:
        """将标题转换为安全的文件名"""
        safe = re.sub(r'[<>:"/\\|?*\u0000-\u001f]', "", name)
        safe = re.sub(r'\s+', "_", safe.strip())
        return safe[:max_len].strip("_") or "untitled"
    
    def download_papers(self, papers: list[dict]) -> list[dict]:
        """
        下载论文 PDF
        
        Args:
            papers: 论文列表, 需含 pdf_url, arxiv_id, evaluation 字段
            
        Returns:
            添加了 local_path 和 is_downloaded 字段的论文列表
        """
        from app.services.llm_service import should_download
        
        save_dir = self.base_path / "data" / "downloads" / self.today / "papers"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"开始下载 {len(papers)} 篇论文 PDF")
        
        for i, paper in enumerate(papers):
            # 检查是否需要下载
            evaluation = paper.get("evaluation", {})
            if not should_download(evaluation):
                paper["local_path"] = None
                paper["is_downloaded"] = False
                logger.debug(f"[{i+1}/{len(papers)}] 跳过 (未通过评估): {paper.get('arxiv_id', '')}")
                continue
            
            pdf_url = paper.get("pdf_url")
            if not pdf_url:
                paper["local_path"] = None
                paper["is_downloaded"] = False
                continue
            
            arxiv_id = paper.get("arxiv_id", "")
            safe_id = arxiv_id.replace("/", "_")
            title = paper.get("title", "")
            title_filename = self._safe_filename(title, max_len=100)
            filename = f"{safe_id}_{title_filename}.pdf"
            file_path = save_dir / filename
            
            # 如果已存在则跳过
            if file_path.exists():
                paper["local_path"] = str(file_path.relative_to(self.base_path))
                paper["is_downloaded"] = True
                logger.debug(f"[{i+1}/{len(papers)}] 已存在: {filename}")
                continue
            
            try:
                logger.debug(f"[{i+1}/{len(papers)}] 下载: {arxiv_id}")
                response = httpx.get(pdf_url, follow_redirects=True, timeout=120.0)
                response.raise_for_status()
                
                file_path.write_bytes(response.content)
                size_kb = len(response.content) / 1024
                
                paper["local_path"] = str(file_path.relative_to(self.base_path))
                paper["is_downloaded"] = True
                logger.info(f"[{i+1}/{len(papers)}] 成功: {filename} ({size_kb:.1f} KB)")
                
            except Exception as e:
                paper["local_path"] = None
                paper["is_downloaded"] = False
                logger.error(f"[{i+1}/{len(papers)}] 失败: {arxiv_id} - {str(e)[:50]}")
        
        success = sum(1 for p in papers if p.get("is_downloaded"))
        logger.info(f"论文 PDF 下载完成: {success}/{len(papers)} 成功")
        return papers
    
    def download_projects(self, projects: list[dict]) -> list[dict]:
        """
        下载项目 README
        
        Args:
            projects: 项目列表, 需含 full_name, evaluation 字段
            
        Returns:
            添加了 local_readme_path 和 is_downloaded 字段的项目列表
        """
        from app.services.llm_service import should_download
        from app.services.github_client import get_repo_readme
        
        save_dir = self.base_path / "data" / "downloads" / self.today / "projects"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"开始下载 {len(projects)} 个项目 README")
        
        for i, project in enumerate(projects):
            # 检查是否需要下载
            evaluation = project.get("evaluation", {})
            if not should_download(evaluation):
                project["local_readme_path"] = None
                project["is_downloaded"] = False
                logger.debug(f"[{i+1}/{len(projects)}] 跳过 (未通过评估): {project.get('full_name', '')}")
                continue
            
            full_name = project.get("full_name", "")
            if not full_name:
                project["local_readme_path"] = None
                project["is_downloaded"] = False
                continue
            
            owner, repo = full_name.split("/", 1) if "/" in full_name else ("", "")
            if not owner or not repo:
                project["local_readme_path"] = None
                project["is_downloaded"] = False
                continue
            
            safe_name = full_name.replace("/", "_")
            filename = f"{safe_name}_README.md"
            file_path = save_dir / filename
            
            # 如果已存在则跳过
            if file_path.exists():
                project["local_readme_path"] = str(file_path.relative_to(self.base_path))
                project["is_downloaded"] = True
                logger.debug(f"[{i+1}/{len(projects)}] 已存在: {filename}")
                continue
            
            try:
                logger.debug(f"[{i+1}/{len(projects)}] 下载: {full_name}")
                readme_content = get_repo_readme(owner, repo)
                
                if readme_content:
                    file_path.write_text(readme_content, encoding="utf-8")
                    size_kb = len(readme_content) / 1024
                    
                    project["local_readme_path"] = str(file_path.relative_to(self.base_path))
                    project["is_downloaded"] = True
                    logger.info(f"[{i+1}/{len(projects)}] 成功: {filename} ({size_kb:.1f} KB)")
                else:
                    project["local_readme_path"] = None
                    project["is_downloaded"] = False
                    logger.warning(f"[{i+1}/{len(projects)}] 无 README: {full_name}")
                    
            except Exception as e:
                project["local_readme_path"] = None
                project["is_downloaded"] = False
                logger.error(f"[{i+1}/{len(projects)}] 失败: {full_name} - {str(e)[:50]}")
        
        success = sum(1 for p in projects if p.get("is_downloaded"))
        logger.info(f"项目 README 下载完成: {success}/{len(projects)} 成功")
        return projects
    
    def download_all(self, papers: list[dict] = None, projects: list[dict] = None) -> tuple[list[dict], list[dict]]:
        """
        统一下载论文和项目
        
        Args:
            papers: 论文列表
            projects: 项目列表
            
        Returns:
            (处理后的论文列表, 处理后的项目列表)
        """
        processed_papers = self.download_papers(papers or []) if papers else []
        processed_projects = self.download_projects(projects or []) if projects else []
        return processed_papers, processed_projects