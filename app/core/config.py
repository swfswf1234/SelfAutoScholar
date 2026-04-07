"""配置读取模块 - 从 setting.ini 和环境变量读取配置"""

import os
from pathlib import Path
from configparser import ConfigParser

from pydantic import Field
from pydantic_settings import BaseSettings


def load_ini_config() -> dict:
    """从 setting.ini 读取配置"""
    config = ConfigParser()
    ini_path = Path(__file__).parent.parent.parent / "setting.ini"
    if ini_path.exists():
        config.read(ini_path, encoding="utf-8")
    return config


class Settings(BaseSettings):
    """应用配置"""

    # === 路径配置 ===
    base_path: str = Field(default=".")
    downloads_dir: str = Field(default="data/downloads")
    exports_dir: str = Field(default="exports/markdown")
    logs_dir: str = Field(default="logs")

    # === 数据库配置 ===
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_name: str = Field(default="selfautoscholar")
    db_user: str = Field(default="postgres")
    db_password: str = Field(default="123456")

    # === 默认用户配置 ===
    default_user: str = Field(default="postgres")

    # === LLM 配置 (OpenAI 兼容) ===
    llm_api_base: str = Field(default="https://api.openai.com/v1")
    llm_api_key: str = Field(default="sk-xxx")
    llm_model: str = Field(default="gpt-4o-mini")

    # === 本地 LLM 配置 ===
    local_llm_api_base: str = Field(default="http://127.0.0.1:5001/v1")
    local_llm_api_key: str = Field(default="lm-studio")
    local_llm_model: str = Field(default="qwen/qwen3.5-9b")

    # === LLM Provider 选择 ===
    # evaluation_provider: 论文评估任务使用哪个 provider (local / external)
    evaluation_provider: str = Field(default="local")
    # reasoning_provider: 推理/分析任务使用哪个 provider (local / external)
    reasoning_provider: str = Field(default="external")

    # === Discovery 配置 ===
    search_keywords: list[str] = Field(
        default=["LLM", "Large Language Model", "NLP", "Machine Learning"]
    )
    max_candidates: int = Field(default=20)
    max_downloads: int = Field(default=10)

    # === API 配置 ===
    api_enable: bool = Field(default=True)
    api_port: int = Field(default=8001)
    api_host: str = Field(default="0.0.0.0")

    # === 安全配置 ===
    api_key: str = Field(default="your_api_key_here")

    # === 日志配置 ===
    log_level: str = Field(default="INFO")

    class Config:
        env_prefix = "SAS_"  # 环境变量前缀

    @property
    def db_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    def get_downloads_path(self) -> Path:
        """获取下载目录的绝对路径"""
        return self.project_root / self.downloads_dir

    def get_exports_path(self) -> Path:
        """获取导出目录的绝对路径"""
        return self.project_root / self.exports_dir


def load_settings_from_ini() -> Settings:
    """从 setting.ini 加载配置并创建 Settings 实例"""
    config = load_ini_config()

    kwargs = {}

    if config.has_section("Paths"):
        sec = config["Paths"]
        kwargs["base_path"] = sec.get("base_path", ".")
        kwargs["downloads_dir"] = sec.get("downloads_dir", "data/downloads")
        kwargs["exports_dir"] = sec.get("exports_dir", "exports/markdown")
        kwargs["logs_dir"] = sec.get("logs_dir", "logs")

    if config.has_section("Postgres"):
        sec = config["Postgres"]
        kwargs["db_host"] = sec.get("host", "localhost")
        kwargs["db_port"] = sec.getint("port", 5432)
        kwargs["db_name"] = sec.get("database", "selfautoscholar")
        kwargs["db_user"] = sec.get("user", "postgres")
        kwargs["db_password"] = sec.get("password", "123456")

    if config.has_section("LLM"):
        sec = config["LLM"]
        kwargs["llm_api_base"] = sec.get("external_api_base", "https://api.openai.com/v1")
        kwargs["llm_api_key"] = sec.get("external_api_key", "sk-xxx")
        kwargs["llm_model"] = sec.get("external_model", "gpt-4o-mini")
        kwargs["local_llm_api_base"] = sec.get("local_api_base", "http://127.0.0.1:5001/v1")
        kwargs["local_llm_api_key"] = sec.get("local_api_key", "lm-studio")
        kwargs["local_llm_model"] = sec.get("local_model", "qwen/qwen3.5-9b")
        kwargs["evaluation_provider"] = sec.get("evaluation_provider", "local")
        kwargs["reasoning_provider"] = sec.get("reasoning_provider", "external")

    if config.has_section("Discovery"):
        sec = config["Discovery"]
        keywords_str = sec.get("search_keywords", "LLM, Large Language Model, NLP, Machine Learning")
        kwargs["search_keywords"] = [k.strip() for k in keywords_str.split(",") if k.strip()]
        kwargs["max_candidates"] = sec.getint("max_candidates", 20)
        kwargs["max_downloads"] = sec.getint("max_downloads", 10)

    if config.has_section("API"):
        sec = config["API"]
        kwargs["api_enable"] = sec.getboolean("enable", True)
        kwargs["api_port"] = sec.getint("port", 8001)
        kwargs["api_host"] = sec.get("host", "0.0.0.0")

    if config.has_section("Security"):
        sec = config["Security"]
        kwargs["api_key"] = sec.get("api_key", "your_api_key_here")

    if config.has_section("Logging"):
        sec = config["Logging"]
        kwargs["log_level"] = sec.get("level", "INFO")

    if config.has_section("User"):
        sec = config["User"]
        kwargs["default_user"] = sec.get("default_user", "postgres")

    return Settings(**kwargs)


# 全局配置实例
settings = load_settings_from_ini()
