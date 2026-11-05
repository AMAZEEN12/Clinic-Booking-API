"""API errors. Every error response has the shape {"error": "<message>"} (R14)."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("app.errors")


class AppError(Exception):
    """Base class for errors we raise on purpose; each maps to one HTTP status."""

    status_code = 500
    default_message = "internal server error"

    def __init__(self, message: str | None = None, headers: dict[str, str] | None = None):
        self.message = message or self.default_message
        self.headers = headers
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = 400
    default_message = "bad request"


class UnauthorizedError(AppError):
    status_code = 401
    default_message = "missing or invalid API key"


class NotFoundError(AppError):
    status_code = 404
    default_message = "not found"


class ConflictError(AppError):
    status_code = 409
    default_message = "conflict"


class UnprocessableError(AppError):
    status_code = 422
    default_message = "unprocessable request"


class TooManyRequestsError(AppError):
    status_code = 429
    default_message = "too many requests"


def error_response(
    status_code: int, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status_code, headers=headers)


def describe_validation_errors(errors: list) -> str:
    """Turn validation errors into a short message without echoing the submitted values (N4)."""
    parts = []
    for err in errors:
        location = ""
        if err.get("type") != "json_invalid":
            for part in err.get("loc", ()):
                if isinstance(part, int):
                    location += f"[{part}]"
                elif part not in ("body", "query", "path"):
                    location += f".{part}" if location else str(part)
        message = err.get("msg", "invalid value")
        parts.append(f"{location}: {message}" if location else message)
    return "; ".join(parts) or "invalid request"


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status_code, exc.message, exc.headers)


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(400, describe_validation_errors(exc.errors()))


async def _handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return error_response(exc.status_code, str(exc.detail).lower(), exc.headers)


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Log only the error type: messages can contain personal data (N4). Never show details (N8).
    log.error("unhandled %s on %s %s", type(exc).__name__, request.method, request.url.path)
    return error_response(500, "internal server error")


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
