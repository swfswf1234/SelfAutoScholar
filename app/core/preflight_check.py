"""启动前校验模块 - 验证数据库和模型连通性

在非 --no-db 模式下执行前置校验：
    1. 数据库连接测试
    2. 数据库表结构检查
    3. 本地模型连通性检测
    4. 外部模型连通性检测
    5. GitHub 配置校验

Usage:
    from app.core.preflight_check import run_preflight_check
    
    result = run_preflight_check()
    if not result["success"]:
        print(result["error_message"])
        return 1
"""

from typing import Any

from openai import OpenAI
from sqlalchemy import inspect, text

from app.core.config import settings


def check_github_config() -> dict[str, Any]:
    """检查 GitHub 配置是否正确
    
    Returns:
        {
            "configured": bool,
            "error": str|None,
            "api_base": str,
            "has_token": bool
        }
    """
    result = {
        "configured": False,
        "error": None,
        "api_base": settings.github_api_base,
        "has_token": bool(settings.github_token),
    }
    
    if not settings.github_token:
        result["error"] = "GitHub Token 未配置，请在 setting.ini [GitHub] 节点设置 github_token"
        return result
    
    import httpx
    try:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {settings.github_token}",
        }
        url = f"{settings.github_api_base}/user"
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers)
            if response.status_code == 200:
                user_data = response.json()
                result["configured"] = True
                result["username"] = user_data.get("login")
            elif response.status_code == 401:
                result["error"] = "GitHub Token 无效或已过期，请在 setting.ini [GitHub] 中更新 github_token"
            else:
                result["error"] = f"GitHub API 返回错误: {response.status_code}"
    except Exception as e:
        result["error"] = f"GitHub 连接失败: {str(e)[:200]}"
    
    return result


def check_database_connection() -> dict[str, Any]:
    """测试数据库连接是否成功
    
    Returns:
        {
            "connected": bool,
            "error": str|None,
            "details": dict|None
        }
    """
    result = {"connected": False, "error": None, "details": None}
    
    try:
        from app.core.database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        result["connected"] = True
    except Exception as e:
        error_msg = str(e).lower()
        
        if "connection refused" in error_msg:
            error = (
                "数据库连接失败: 连接被拒绝\n"
                "可能原因:\n"
                "  1. PostgreSQL 服务未启动\n"
                "  2. 配置的 host/port 错误\n"
                "  3. 防火墙阻止连接\n"
            )
        elif "authentication failed" in error_msg or "password" in error_msg:
            error = (
                "数据库连接失败: 认证失败\n"
                "可能原因:\n"
                "  1. 用户名或密码错误\n"
                "  2. 用户没有连接权限\n"
            )
        elif "could not translate host" in error_msg or "name or service not known" in error_msg:
            error = (
                "数据库连接失败: 无法解析主机名\n"
                "可能原因:\n"
                "  1. 配置的 host 错误\n"
                "  2. 网络不可达\n"
            )
        elif "database" in error_msg and "does not exist" in error_msg:
            error = (
                "数据库连接失败: 数据库不存在\n"
                f"  请创建数据库: {settings.db_name}\n"
                "  命令: CREATE DATABASE selfautoscholar;"
            )
        else:
            error = f"数据库连接失败: {str(e)[:200]}"
        
        result["error"] = error
        result["details"] = {"exception": str(e)}
    
    return result


def check_database_schema() -> dict[str, Any]:
    """检查数据库表是否完整
    
    Returns:
        {
            "tables_ok": bool,
            "error": str|None,
            "existing_tables": list[str],
            "missing_tables": list[str]
        }
    """
    result = {
        "tables_ok": False,
        "error": None,
        "existing_tables": [],
        "missing_tables": []
    }
    
    required_tables = {"users", "papers", "projects", "news", "materials", "user_labels"}
    
    try:
        from app.core.database import engine
        inspector = inspect(engine)
        existing = set(inspector.get_table_names())
        
        result["existing_tables"] = list(existing)
        result["missing_tables"] = list(required_tables - existing)
        
        if result["missing_tables"]:
            result["error"] = (
                f"数据库表不完整，缺少以下表:\n"
                f"  {', '.join(sorted(result['missing_tables']))}\n"
                f"请运行数据库初始化创建这些表"
            )
        else:
            result["tables_ok"] = True
            
    except Exception as e:
        result["error"] = f"检查数据库表失败: {str(e)[:200]}"
    
    return result


def check_local_model() -> dict[str, Any]:
    """检查本地模型是否可用
    
    Returns:
        {
            "available": bool,
            "error": str|None,
            "model": str
        }
    """
    result = {"available": False, "error": None, "model": settings.local_llm_model}
    
    try:
        client = OpenAI(
            base_url=settings.local_llm_api_base,
            api_key=settings.local_llm_api_key or "not-needed",
            timeout=30.0,
        )
        
        response = client.chat.completions.create(
            model=settings.local_llm_model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10,
        )
        
        if response.choices[0].message.content is not None:
            result["available"] = True
        else:
            result["error"] = "本地模型响应为空"
            
    except Exception as e:
        error_msg = str(e).lower()
        
        if "connection" in error_msg or "connect" in error_msg:
            error = (
                "本地模型连接失败: 无法连接到 LM Studio\n"
                "可能原因:\n"
                "  1. LM Studio 未启动\n"
                "  2. 端口配置错误 (当前: {})\n"
                "  3. 模型未加载\n"
            ).format(settings.local_llm_api_base)
        elif "404" in error_msg or "not found" in error_msg:
            error = (
                f"本地模型不可用: 模型未找到\n"
                f"  配置的模型: {settings.local_llm_model}\n"
                f"  请在 LM Studio 中加载模型\n"
            )
        elif "timeout" in error_msg:
            error = (
                "本地模型响应超时\n"
                "可能原因:\n"
                "  1. 模型加载中\n"
                "  2. 模型太大导致响应慢\n"
            )
        else:
            error = f"本地模型调用失败: {str(e)[:200]}"
        
        result["error"] = error
    
    return result


def check_external_model() -> dict[str, Any]:
    """检查外部模型是否可用
    
    Returns:
        {
            "available": bool,
            "error": str|None,
            "model": str
        }
    """
    result = {"available": False, "error": None, "model": settings.llm_model}
    
    try:
        client = OpenAI(
            base_url=settings.llm_api_base,
            api_key=settings.llm_api_key,
            timeout=30.0,
        )
        
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10,
        )
        
        if response.choices[0].message.content is not None:
            result["available"] = True
            
    except Exception as e:
        error_msg = str(e).lower()
        
        if "connection" in error_msg or "connect" in error_msg:
            error = (
                "外部模型连接失败: 无法连接到 API\n"
                "可能原因:\n"
                "  1. 网络无法访问外部 API\n"
                "  2. API 地址配置错误\n"
            )
        elif "401" in error_msg or "unauthorized" in error_msg:
            error = (
                "外部模型认证失败: API Key 无效\n"
                "请检查 setting.ini 中的 external_api_key\n"
            )
        elif "403" in error_msg or "forbidden" in error_msg:
            error = (
                "外部模型权限被拒绝\n"
                "可能原因:\n"
                "  1. API Key 已过期\n"
                "  2. 账户余额不足\n"
            )
        elif "404" in error_msg or "not found" in error_msg:
            error = (
                f"外部模型不存在: {settings.llm_model}\n"
                f"请检查模型名称是否正确\n"
            )
        elif "timeout" in error_msg:
            error = "外部模型响应超时，请检查网络状况"
        else:
            error = f"外部模型调用失败: {str(e)[:200]}"
        
        result["error"] = error
    
    return result


def run_preflight_check(enable_db: bool = True, enable_github: bool = True) -> dict[str, Any]:
    """运行所有前置校验
    
    Args:
        enable_db: 是否启用数据库校验（等同于 --no-db 模式）
        enable_github: 是否启用 GitHub 校验
    
    Returns:
        {
            "success": bool,
            "database": dict,
            "local_model": dict,
            "external_model": dict,
            "github": dict,
            "error_message": str|None,
            "use_local_model": bool
        }
    """
    result = {
        "success": True,
        "database": {"connected": False, "tables_ok": False, "skipped": not enable_db},
        "local_model": {"available": False, "error": None},
        "external_model": {"available": False, "error": None},
        "github": {"configured": False, "error": None},
        "error_message": None,
        "use_local_model": True,
    }
    
    print("\n" + "=" * 60)
    print("  启动前校验")
    print("=" * 60)
    
    # 1. 数据库校验
    if enable_db:
        print("\n[1/5] 检查数据库连接...")
        db_conn = check_database_connection()
        result["database"]["connected"] = db_conn["connected"]
        
        if not db_conn["connected"]:
            result["success"] = False
            result["error_message"] = db_conn["error"]
            print(f"  [失败] {db_conn['error']}")
            print("\n[错误] 数据库连接失败，无法继续运行")
            return result
        
        print("  [成功] 数据库连接正常")
        
        print("\n[2/5] 检查数据库表结构...")
        db_schema = check_database_schema()
        result["database"]["tables_ok"] = db_schema["tables_ok"]
        
        if not db_schema["tables_ok"]:
            result["success"] = False
            result["error_message"] = db_schema["error"]
            print(f"  [失败] {db_schema['error']}")
            print("\n[错误] 数据库表不完整，无法继续运行")
            return result
        
        print(f"  [成功] 数据库表完整 ({', '.join(db_schema['existing_tables'])})")
    
    # 2. 本地模型校验
    print("\n[3/5] 检查本地模型...")
    local_model = check_local_model()
    result["local_model"] = local_model
    
    if not local_model["available"]:
        result["success"] = False
        result["error_message"] = local_model["error"]
        print(f"  [失败] {local_model['error']}")
        print("\n[错误] 本地模型不可用，无法继续运行")
        return result
    
    print(f"  [成功] 本地模型可用 ({local_model['model']})")
    
    # 3. 外部模型校验
    print("\n[4/5] 检查外部模型...")
    external_model = check_external_model()
    result["external_model"] = external_model
    
    if external_model["available"]:
        print(f"  [成功] 外部模型可用 ({external_model['model']})")
    else:
        print(f"  [提示] 外部模型不可用: {external_model['error'][:80]}...")
        print("  将使用本地模型进行评估")
        result["use_local_model"] = True
    
    # 4. GitHub 校验
    if enable_github:
        print("\n[5/5] 检查 GitHub 配置...")
        github_config = check_github_config()
        result["github"] = github_config
        
        if not github_config["configured"]:
            result["success"] = False
            result["error_message"] = github_config["error"]
            print(f"  [失败] {github_config['error']}")
            print("\n[错误] GitHub 配置错误，无法继续运行")
            return result
        
        print(f"  [成功] GitHub 配置正确 (用户: {github_config.get('username', 'N/A')})")
    else:
        print("\n[5/5] 检查 GitHub 配置... [跳过]")
    
    print("\n" + "=" * 60)
    print("  校验完成")
    print("=" * 60)
    
    return result
