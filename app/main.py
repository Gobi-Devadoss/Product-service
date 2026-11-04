import logging
import time

from fastapi import FastAPI, Request

from app.config import settings
from app.errors import register_error_handlers
from app.routers import health, products

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("product_service.requests")

app = FastAPI(
    title="Product Service",
    version="1.0.0",
    description="Manages products for the online store.",
)

register_error_handlers(app)
app.include_router(products.router)
app.include_router(health.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s (%.1f ms)", request.method, request.url.path, response.status_code, elapsed_ms
    )
    return response
