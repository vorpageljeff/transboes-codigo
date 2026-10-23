from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.business import router as business_router
from app.api.v1.financial import router as financial_router
from app.api.v1.imports import router as imports_router
from app.api.v1.mvp import router as mvp_router
from app.api.v1.router import router as api_router
from app.api.v1.tracking import router as tracking_router
from app.core.config import settings
from app.core.request_limits import BoundedBody, request_limits
from app.db.session import engine

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(BoundedBody)
app.middleware("http")(request_limits)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(business_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api/v1")
app.include_router(financial_router, prefix="/api/v1")
app.include_router(imports_router, prefix="/api/v1")
app.include_router(mvp_router, prefix="/api/v1")
app.include_router(tracking_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}
