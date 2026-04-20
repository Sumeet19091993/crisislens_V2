from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from .logging_setup import configure_logging
from .middleware import request_log_middleware
from .routers.analytics import router as analytics_router
from .routers.auth import router as auth_router
from .routers.health import router as health_router
from .routers.live import router as live_router
from .routers.reports import router as reports_router

configure_logging()

app = FastAPI(title="CrisisLens API")

app.middleware("http")(request_log_middleware)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(reports_router)
app.include_router(live_router)
app.include_router(analytics_router)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)