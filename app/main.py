"""QED-Tracker FastAPI 入口"""

import sys
import io

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"QED-Tracker 启动: dataset={settings.dataset_path}")
    yield
    logger.info("QED-Tracker 关闭")


app = FastAPI(
    title="QED-Tracker API",
    description="QED-Engine 数学资源检索与分类引擎",
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "service": "QED-Tracker",
        "version": "0.2.0",
        "dataset": str(settings.dataset_path),
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.api_host, port=8001, reload=True)
