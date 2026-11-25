from fastapi import FastAPI
from api.main import api_router
from core.config import settings

app = FastAPI()


app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        docs_url=f"{settings.API_PREFIX}/docs",
        redoc_url=f"{settings.API_PREFIX}/redoc",
        # lifespan=lifespan,
    )

app.include_router(api_router, prefix=settings.API_PREFIX)