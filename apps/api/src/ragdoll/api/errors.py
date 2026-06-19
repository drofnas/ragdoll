from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ragdoll.core.exceptions import ApplicationError

PROBLEM_CONTENT_TYPE = "application/problem+json"


def _problem_response(
    request: Request,
    *,
    type_: str,
    title: str,
    status: int,
    detail: str,
    code: str | None = None,
) -> JSONResponse:
    payload = {
        "type": type_,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": str(request.url),
    }
    if code is not None:
        payload["code"] = code
    return JSONResponse(
        status_code=status,
        content=payload,
        media_type=PROBLEM_CONTENT_TYPE,
    )


async def handle_application_error(request: Request, exc: ApplicationError) -> JSONResponse:
    """Translate application exceptions into a stable problem response."""
    return _problem_response(
        request,
        type_=exc.type_uri,
        title=exc.title,
        status=exc.status_code,
        detail=exc.detail,
        code=exc.code,
    )


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Translate request validation failures into a stable problem response."""
    return _problem_response(
        request,
        type_="https://ragdoll.dev/problems/request-validation",
        title="Request validation failed",
        status=422,
        detail="The request payload or parameters did not match the expected schema.",
        code="request_validation_failed",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register shared exception handlers on the FastAPI app."""
    app.add_exception_handler(ApplicationError, handle_application_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
