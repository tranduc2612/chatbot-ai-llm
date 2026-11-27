import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.main import api_router
from core.config import settings
from core.database import close_db
from core.db_bootstrap import ensure_database_exists
from core.migrations import run_migrations
from core.seed import ensure_admin_user

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Tạo database nếu chưa có  2. Đưa schema lên Alembic head  3. Tạo admin mặc định
    # Lỗi ở đây sẽ dừng server, không chạy với DB sai cấu trúc.
    await ensure_database_exists()
    await run_migrations()
    await ensure_admin_user()
    yield
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.API_PREFIX)
