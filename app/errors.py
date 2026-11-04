"""Global error handlers: every error leaves the API in the same JSON shape."""

import logging
from datetime import datetime, timezone
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import AppError

logger = logging.getLogger("product_service.errors")


def error_response(request: Request, status: int, message: str, details=None) -> JSONResponse:
    body = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "error": HTTPStatus(status).phrase,
        "message": message,
        "path": request.url.path,
        "details": details or [],
    }
    return JSONResponse(status_code=status, content=body)


async def handle_app_error(request: Request, exc: AppError):
    logger.info("%s %s -> %s: %s", request.method, request.url.path, exc.status_code, exc.message)
    return error_response(request, exc.status_code, exc.message, exc.details)


async def handle_validation_error(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if any(e["type"] == "json_invalid" for e in errors):
        logger.warning("%s %s -> 400: malformed JSON", request.method, request.url.path)
        return error_response(request, 400, "Malformed JSON")

    # A body sent without a JSON content type (e.g. Postman "raw > Text") is never parsed
    content_type = request.headers.get("content-type", "")
    if "json" not in content_type and any(e["loc"] == ("body",) for e in errors):
        message = "Request body must be JSON; send header Content-Type: application/json"
        logger.warning("%s %s -> 400: %s (got %r)", request.method, request.url.path, message, content_type)
        return error_response(request, 400, message)

    details = []
    for e in errors:
        field = ".".join(str(p) for p in e["loc"] if p not in ("body", "query", "path")) or "body"
        issue = e["msg"].removeprefix("Value error, ")
        details.append({"field": field, "issue": issue})
    logger.warning("%s %s -> 400: validation failed %s", request.method, request.url.path, details)
    return error_response(request, 400, "Validation failed", details)


async def handle_http_error(request: Request, exc: StarletteHTTPException):
    message = exc.detail if isinstance(exc.detail, str) else HTTPStatus(exc.status_code).phrase
    return error_response(request, exc.status_code, message)


async def handle_unexpected_error(request: Request, exc: Exception):
   
    logger.exception("Unexpected error on %s %s", request.method, request.url.path)
    return error_response(request, 500, "An unexpected error occurred")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
