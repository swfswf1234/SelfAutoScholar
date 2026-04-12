"""统一报告生成服务

功能:
    - 生成每日 Markdown 简报 (论文 + 项目)
    - 支持按类别分组显示
    - 支持评估结果摘要
    
Usage:
    from app.services.report_generator import ReportGenerator
    
    generator = ReportGenerator(base_path)
    report_path = generator.generate(papers, projects, date_str)
"""

import json
from pathlib import Path
from datetime import date
from typing import Any


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, base_path: Path):
        """
        初始化报告生成器
        
        Args:
            base_path: 项目根目录
        """
        self.base_path = base_path
    
    def _format_paper(self, paper: dict, index: int) -> str:
        """格式化单篇论文为 Markdown"""
        title = paper.get("title", "无标题")
        arxiv_id = paper.get("arxiv_id", "")
        authors = ", ".join(paper.get("authors", [])[:3])
        if len(paper.get("authors", [])) > 3:
            authors += " 等"
        
        ev = paper.get("evaluation", {})
        imp = "Y" if ev.get("is_important") else "N"
        rel = "Y" if ev.get("is_relevant") else "N"
        int_ = "Y" if ev.get("is_interested") else "N"
        
        local_path = paper.get("local_path", "")
        pdf_link = f"[本地 PDF]({local_path})" if local_path else ""
        
        abstract = paper.get("abstract", "")
        if len(abstract) > 400:
            abstract = abstract[:400] + "..."
        
        lines = [
            f"## {index}. {title}\n",
            f"- **arXiv ID**: [{arxiv_id}](https://arxiv.org/abs/{arxiv_id})\n",
            f"- **作者**: {authors}\n",
            f"- **发布日期**: {paper.get('published_date', 'N/A')}\n",
            f"- **评估**: 重要[{imp}] 相关[{rel}] 感兴趣[{int_}]\n",
        ]
        if pdf_link:
            lines.append(f"- **PDF**: {pdf_link}\n")
        
        lines.append(f"\n**摘要**: {abstract}\n")
        return "".join(lines)
    
    def _format_project(self, project: dict, index: int) -> str:
        """格式化单个项目为 Markdown"""
        full_name = project.get("full_name", "无名称")
        name = project.get("name", "")
        description = project.get("description", "") or "无描述"
        
        ev = project.get("evaluation", {})
        imp = "Y" if ev.get("is_important") else "N"
        rel = "Y" if ev.get("is_relevant") else "N"
        int_ = "Y" if ev.get("is_interested") else "N"
        
        stars = project.get("stars", 0)
        forks = project.get("forks", 0)
        language = project.get("language", "N/A")
        
        local_readme = project.get("local_readme_path", "")
        readme_link = f"[本地 README]({local_readme})" if local_readme else ""
        
        html_url = project.get("html_url", "")
        github_link = f"[GitHub]({html_url})" if html_url else ""
        
        lines = [
            f"## {index}. {full_name}\n",
            f"- **Stars**: {stars} | **Forks**: {forks}\n",
            f"- **语言**: {language}\n",
            f"- **评估**: 重要[{imp}] 相关[{rel}] 感兴趣[{int_}]\n",
        ]
        if github_link:
            lines.append(f"- **链接**: {github_link}\n")
        if readme_link:
            lines.append(f"- **README**: {readme_link}\n")
        
        lines.append(f"\n**描述**: {description[:300]}\n")
        return "".join(lines)
    
    def generate(self, papers: list[dict] = None, projects: list[dict] = None, date_str: str = None) -> Path:
        """
        生成 Markdown 简报
        
        Args:
            papers: 论文列表
            projects: 项目列表
            date_str: 日期字符串 (默认今天)
            
        Returns:
            生成的报告文件路径
        """
        if date_str is None:
            date_str = date.today().strftime("%Y-%m-%d")
        
        # 输出目录
        export_dir = self.base_path / "exports" / "markdown"
        export_dir.mkdir(parents=True, exist_ok=True)
        report_path = export_dir / f"{date_str}.md"
        
        # 统计
        total_papers = len(papers or [])
        total_projects = len(projects or [])
        
        important_papers = sum(1 for p in (papers or []) if p.get("evaluation", {}).get("is_important"))
        relevant_papers = sum(1 for p in (papers or []) if p.get("evaluation", {}).get("is_relevant"))
        downloaded_papers = sum(1 for p in (papers or []) if p.get("is_downloaded"))
        
        important_projects = sum(1 for p in (projects or []) if p.get("evaluation", {}).get("is_important"))
        relevant_projects = sum(1 for p in (projects or []) if p.get("evaluation", {}).get("is_relevant"))
        downloaded_projects = sum(1 for p in (projects or []) if p.get("is_downloaded"))
        
        # 生成 Markdown
        lines = [
            f"# 每日资讯简报\n",
            f"> 生成日期: {date_str} | 论文: {total_papers} 篇 | 项目: {total_projects} 个\n",
            f"---\n",
            f"\n## 统计摘要\n",
            f"- **论文**: 总计 {total_papers} 篇 | 重要 {important_papers} | 相关 {relevant_papers} | 已下载 {downloaded_papers}\n",
            f"- **项目**: 总计 {total_projects} 个 | 重要 {important_projects} | 相关 {relevant_projects} | 已下载 {downloaded_projects}\n",
            f"\n---\n",
        ]
        
        # 论文部分
        if papers:
            lines.append(f"\n## 论文 ({total_papers} 篇)\n")
            downloaded = [p for p in papers if p.get("is_downloaded")]
            if downloaded:
                for i, p in enumerate(downloaded, 1):
                    lines.append(self._format_paper(p, i))
                    lines.append("---\n\n")
            else:
                lines.append("_无已下载论文_\n")
        
        # 项目部分
        if projects:
            lines.append(f"\n## 项目 ({total_projects} 个)\n")
            downloaded = [p for p in projects if p.get("is_downloaded")]
            if downloaded:
                for i, p in enumerate(downloaded, 1):
                    lines.append(self._format_project(p, i))
                    lines.append("---\n\n")
            else:
                lines.append("_无已下载项目_\n")
        
        # 写入文件
        with open(report_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        return report_path
    
    def export_json(self, papers: list[dict] = None, projects: list[dict] = None, date_str: str = None) -> Path:
        """
        导出 JSON 格式详情
        
        Args:
            papers: 论文列表
            projects: 项目列表
            date_str: 日期字符串
            
        Returns:
            生成的 JSON 文件路径
        """
        if date_str is None:
            date_str = date.today().strftime("%Y-%m-%d")
        
        # 输出目录
        download_dir = self.base_path / "data" / "downloads" / date_str
        download_dir.mkdir(parents=True, exist_ok=True)
        
        # 论文 JSON
        if papers:
            papers_path = download_dir / "papers_detail.json"
            export_papers = []
            for p in papers:
                export_papers.append({
                    "arxiv_id": p.get("arxiv_id"),
                    "title": p.get("title"),
                    "authors": p.get("authors"),
                    "published_date": str(p.get("published_date", "")),
                    "categories": p.get("categories"),
                    "abstract": p.get("abstract"),
                    "source_url": p.get("source_url"),
                    "pdf_url": p.get("pdf_url"),
                    "local_path": p.get("local_path", ""),
                    "is_downloaded": p.get("is_downloaded", False),
                    "evaluation": p.get("evaluation", {}),
                })
            with open(papers_path, "w", encoding="utf-8") as f:
                json.dump(export_papers, f, ensure_ascii=False, indent=2)
        
        # 项目 JSON
        if projects:
            projects_path = download_dir / "projects_detail.json"
            export_projects = []
            for p in projects:
                export_projects.append({
                    "full_name": p.get("full_name"),
                    "name": p.get("name"),
                    "owner": p.get("owner"),
                    "description": p.get("description"),
                    "html_url": p.get("html_url"),
                    "stars": p.get("stars", 0),
                    "forks": p.get("forks", 0),
                    "language": p.get("language"),
                    "topics": p.get("topics", []),
                    "license": p.get("license"),
                    "local_readme_path": p.get("local_readme_path", ""),
                    "is_downloaded": p.get("is_downloaded", False),
                    "evaluation": p.get("evaluation", {}),
                })
            with open(projects_path, "w", encoding="utf-8") as f:
                json.dump(export_projects, f, ensure_ascii=False, indent=2)
        
        return download_dir