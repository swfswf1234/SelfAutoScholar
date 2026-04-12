"""SelfAutoScholar 统一入口 - arXiv 论文 + GitHub 项目完整流程

功能:
    1. 预检验证 (数据库 + 本地模型 + GitHub 配置)
    2. 搜索 arXiv 论文 (按关键词)
    3. 搜索 GitHub 项目 (按关键词)
    4. 统一去重
    5. LLM 评估 (重要性/相关性/兴趣)
    6. 下载与存储 (论文 PDF + 项目 README)
    7. 生成报告 (Markdown 简报 + JSON 详情)

使用方式:
    # 完整流程 (arXiv + GitHub)
    python -m app.main --source all
    
    # 仅 arXiv 论文
    python -m app.main --source arxiv
    
    # 仅 GitHub 项目
    python -m app.main --source github
    
    # 指定关键词
    python -m app.main --source all --keywords "LLM,RAG"
    
    # 跳过数据库模式
    python -m app.main --source all --no-db
    
    # 跳过预检验证
    python -m app.main --source all --skip-preflight
"""

import sys
import io
import argparse
from pathlib import Path
from datetime import date

# Windows 控制台 UTF-8 输出修复
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

# 禁用 loguru 全局日志
import loguru
loguru.logger.disable("loguru")

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.core.preflight_check import run_preflight_check, check_local_model, check_github_config
from app.services.arxiv_client import search_by_keywords as search_arxiv
from app.services.github_client import search_repositories
from app.services.llm_service import LLMService, should_download
from app.services.dedup import DedupService
from app.services.download_manager import DownloadManager
from app.services.report_generator import ReportGenerator
from app.models.paper import Paper
from app.models.project import Project


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="SelfAutoScholar - 每日资讯聚合系统")
    parser.add_argument(
        "--source", 
        type=str, 
        default="all",
        choices=["all", "arxiv", "github"],
        help="数据源: all=论文+项目, arxiv=仅论文, github=仅项目"
    )
    parser.add_argument(
        "--keywords", 
        type=str, 
        default="",
        help="搜索关键词 (逗号分隔), 覆盖配置文件"
    )
    parser.add_argument(
        "--max-per-source", 
        type=int, 
        default=20,
        help="每个数据源最大返回数量"
    )
    parser.add_argument(
        "--language", 
        type=str, 
        default="python",
        help="GitHub 项目语言筛选"
    )
    parser.add_argument(
        "--no-db", 
        action="store_true",
        help="跳过数据库连接"
    )
    parser.add_argument(
        "--skip-preflight", 
        action="store_true",
        help="跳过预检验证"
    )
    return parser.parse_args()


def run_preflight(skip_db: bool = False) -> dict:
    """运行预检验证"""
    print("=" * 60)
    print("  预检验证")
    print("=" * 60)
    
    # 1. 检查本地模型
    print("\n[1/2] 检查本地模型...")
    local_model = check_local_model()
    if not local_model["available"]:
        print(f"  [失败] {local_model['error']}")
        return {"success": False, "error": f"本地模型: {local_model['error']}"}
    print(f"  [成功] 本地模型可用 ({local_model['model']})")
    
    # 2. 检查 GitHub 配置
    print("\n[2/2] 检查 GitHub 配置...")
    github_config = check_github_config()
    if not github_config["configured"]:
        print(f"  [失败] {github_config['error']}")
        return {"success": False, "error": f"GitHub: {github_config['error']}"}
    print(f"  [成功] GitHub 配置正确 (用户: {github_config.get('username', 'N/A')})")
    
    # 3. 检查数据库 (可选)
    if not skip_db:
        print("\n[3/3] 检查数据库连接...")
        try:
            init_db()
            db = SessionLocal()
            db.execute("SELECT 1")
            db.close()
            print("  [成功] 数据库连接正常")
        except Exception as e:
            print(f"  [警告] 数据库连接失败: {str(e)[:60]}")
            print("  将以无数据库模式运行")
    
    print("\n" + "=" * 60)
    print("  预检通过")
    print("=" * 60)
    return {"success": True}


def search_papers(keywords: list[str], max_results: int) -> list[dict]:
    """搜索 arXiv 论文"""
    print(f"\n[步骤 1/7] 搜索 arXiv 论文, 关键词: {keywords}")
    papers = search_arxiv(keywords, max_per_keyword=max_results)
    print(f"  搜索到 {len(papers)} 篇论文")
    return papers


def search_projects(keywords: list[str], max_results: int, language: str) -> list[dict]:
    """搜索 GitHub 项目"""
    from app.services.github_client import search_repositories
    
    print(f"\n[步骤 2/7] 搜索 GitHub 项目, 关键词: {keywords}, 语言: {language}")
    all_projects = []
    for kw in keywords:
        projects = search_repositories(kw, language=language, max_results=max_results)
        all_projects.extend(projects)
    
    # 去重
    dedup = DedupService()
    unique_projects = dedup.dedup_projects(all_projects)
    print(f"  搜索到 {len(unique_projects)} 个项目 (去重后)")
    return unique_projects


def evaluate_items(papers: list[dict], projects: list[dict]) -> tuple[list[dict], list[dict]]:
    """LLM 评估"""
    llm = LLMService()
    
    if papers:
        print(f"\n[步骤 3/7] 评估 {len(papers)} 篇论文")
        papers = llm.evaluate_papers(papers)
    
    if projects:
        print(f"\n[步骤 4/7] 评估 {len(projects)} 个项目")
        # TODO: 实现项目评估 (复用 evaluate_papers 逻辑)
        for i, proj in enumerate(projects):
            proj["evaluation"] = {"is_important": True, "is_relevant": True, "is_interested": True}
            print(f"  [{i+1}/{len(projects)}] {proj.get('full_name', '')} -> 重要=Y 相关=Y 有趣=Y")
    
    return papers, projects


def make_download_decision(papers: list[dict], projects: list[dict]) -> tuple[list[dict], list[dict]]:
    """下载决策"""
    print(f"\n[步骤 5/7] 下载决策...")
    
    # 论文
    papers_to_download = [p for p in papers if should_download(p.get("evaluation", {}))]
    papers_to_download = papers_to_download[:settings.max_downloads]
    for p in papers:
        p["_should_download"] = should_download(p.get("evaluation", {}))
    
    # 项目
    projects_to_download = [p for p in projects if should_download(p.get("evaluation", {}))]
    projects_to_download = projects_to_download[:settings.max_downloads]
    for p in projects:
        p["_should_download"] = should_download(p.get("evaluation", {}))
    
    print(f"  论文: {len(papers_to_download)} 篇将下载 (共 {len(papers)} 篇)")
    print(f"  项目: {len(projects_to_download)} 个将下载 (共 {len(projects)} 个)")
    
    return papers, projects


def download_items(papers: list[dict], projects: list[dict], base_path: Path) -> tuple[list[dict], list[dict]]:
    """下载论文和项目"""
    print(f"\n[步骤 6/7] 下载与存储...")
    
    manager = DownloadManager(base_path)
    papers, projects = manager.download_all(papers, projects)
    
    downloaded_papers = sum(1 for p in papers if p.get("is_downloaded"))
    downloaded_projects = sum(1 for p in projects if p.get("is_downloaded"))
    print(f"  论文下载: {downloaded_papers}/{len(papers)}")
    print(f"  项目下载: {downloaded_projects}/{len(projects)}")
    
    return papers, projects


def save_to_database(papers: list[dict], projects: list[dict]) -> tuple[int, int]:
    """将论文和项目数据写入数据库"""
    print(f"\n[步骤 6/8] 写入数据库...")
    
    db = SessionLocal()
    saved_papers = 0
    saved_projects = 0
    
    try:
        # 保存论文
        for paper in papers:
            ev = paper.get("evaluation", {})
            if not should_download(ev):
                continue
            
            # 检查是否已存在
            existing = db.query(Paper).filter(Paper.arxiv_id == paper.get("arxiv_id")).first()
            if existing:
                print(f"  [跳过] 论文已存在: {paper.get('arxiv_id')}")
                continue
            
            db_paper = Paper(
                arxiv_id=paper.get("arxiv_id"),
                title=paper.get("title"),
                abstract=paper.get("abstract"),
                authors=paper.get("authors", []),
                categories=paper.get("categories", []),
                source_url=paper.get("source_url"),
                pdf_url=paper.get("pdf_url"),
                local_path=paper.get("local_path"),
                is_important=ev.get("is_important"),
                is_relevant=ev.get("is_relevant"),
                is_interested=ev.get("is_interested"),
                is_downloaded=paper.get("is_downloaded", False),
                published_date=paper.get("published_date"),
            )
            db.add(db_paper)
            saved_papers += 1
        
        # 保存项目
        for project in projects:
            ev = project.get("evaluation", {})
            if not should_download(ev):
                continue
            
            # 检查是否已存在
            existing = db.query(Project).filter(Project.github_id == project.get("full_name")).first()
            if existing:
                print(f"  [跳过] 项目已存在: {project.get('full_name')}")
                continue
            
            db_project = Project(
                github_id=project.get("full_name"),
                name=project.get("name"),
                full_name=project.get("full_name"),
                description=project.get("description"),
                source_url=project.get("html_url"),
                local_readme_path=project.get("local_readme_path"),
                stars=project.get("stars", 0),
                forks=project.get("forks", 0),
                language=project.get("language"),
                topics=project.get("topics", []),
                license=project.get("license"),
                is_important=ev.get("is_important"),
                is_relevant=ev.get("is_relevant"),
                is_interested=ev.get("is_interested"),
                is_downloaded=project.get("is_downloaded", False),
            )
            db.add(db_project)
            saved_projects += 1
        
        db.commit()
        print(f"  已保存: {saved_papers} 篇论文, {saved_projects} 个项目")
        
    except Exception as e:
        db.rollback()
        print(f"  [错误] 数据库写入失败: {e}")
    finally:
        db.close()
    
    return saved_papers, saved_projects


def generate_reports(papers: list[dict], projects: list[dict], base_path: Path) -> tuple[Path, Path]:
    """生成报告"""
    print(f"\n[步骤 8/8] 生成报告...")
    
    generator = ReportGenerator(base_path)
    today = date.today().strftime("%Y-%m-%d")
    
    # Markdown 简报
    md_path = generator.generate(papers, projects, today)
    print(f"  Markdown 简报: {md_path}")
    
    # JSON 详情
    json_dir = generator.export_json(papers, projects, today)
    print(f"  JSON 详情: {json_dir}")
    
    return md_path, json_dir


def main():
    """主流程"""
    args = parse_args()
    
    # 确定关键词
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()] if args.keywords else settings.search_keywords
    
    # 项目根目录
    project_root = Path(__file__).parent.parent
    today_str = date.today().strftime("%Y-%m-%d")
    
    print("=" * 70)
    print("  SelfAutoScholar 每日资讯聚合系统")
    print("=" * 70)
    print(f"  数据源: {args.source}")
    print(f"  关键词: {keywords}")
    print(f"  最大结果: {args.max_per_source}")
    print(f"  GitHub 语言: {args.language}")
    print(f"  数据库: {'跳过' if args.no_db else '启用'}")
    print(f"  预检: {'跳过' if args.skip_preflight else '启用'}")
    print("=" * 70)
    
    # 预检验证
    if not args.skip_preflight:
        preflight = run_preflight(skip_db=args.no_db)
        if not preflight["success"]:
            print(f"\n[错误] 预检失败: {preflight['error']}")
            return 1
    
    # 初始化变量
    papers = []
    projects = []
    
    # 搜索
    if args.source in ["all", "arxiv"]:
        papers = search_papers(keywords, args.max_per_source)
    
    if args.source in ["all", "github"]:
        projects = search_projects(keywords, args.max_per_source, args.language)
    
    # 去重
    if papers or projects:
        print(f"\n[去重] 论文: {len(papers)} 篇, 项目: {len(projects)} 个")
        # 注: search_by_keywords 已内置去重，这里保留接口
    
    # 评估
    if papers or projects:
        papers, projects = evaluate_items(papers, projects)
    
    # 下载决策
    if papers or projects:
        papers, projects = make_download_decision(papers, projects)
    
    # 下载
    if papers or projects:
        papers, projects = download_items(papers, projects, project_root)
    
    # 写入数据库 (仅在非 --no-db 模式下)
    if (papers or projects) and not args.no_db:
        save_to_database(papers, projects)
    
    # 生成报告
    if papers or projects:
        generate_reports(papers, projects, project_root)
    
    # 打印总结
    print("\n" + "=" * 70)
    print("  执行完成")
    print("=" * 70)
    print(f"  论文: {len(papers)} 篇, 已下载 {sum(1 for p in papers if p.get('is_downloaded'))} 篇")
    print(f"  项目: {len(projects)} 个, 已下载 {sum(1 for p in projects if p.get('is_downloaded'))} 个")
    print(f"  日期: {today_str}")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())