from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.application.exceptions import (
    ConflictError,
    InvalidCredentialsError,
    InvalidTokenError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

_STATUS_BY_EXCEPTION = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    ValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    InvalidTokenError: status.HTTP_400_BAD_REQUEST,
    ServiceUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


def register_exception_handlers(app: FastAPI) -> None:
    for exc_type, status_code in _STATUS_BY_EXCEPTION.items():

        def handler(
            _request: Request, exc: Exception, status_code: int = status_code
        ) -> JSONResponse:
            return JSONResponse(status_code=status_code, content={"detail": str(exc)})

        app.add_exception_handler(exc_type, handler)
