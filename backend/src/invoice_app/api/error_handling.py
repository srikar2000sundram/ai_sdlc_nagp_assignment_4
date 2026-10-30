"""How failures become HTTP responses. This is the only place that knows both domain errors and status codes."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from invoice_app.domain.errors import (
    ApprovalNotPermittedError,
    DomainValidationError,
    InvalidStateError,
    InvoiceNotFoundError,
)

# Domain failures map to HTTP statuses here, never inside the domain or the routers.
ERROR_STATUS = {
    InvoiceNotFoundError: 404,
    InvalidStateError: 409,
    ApprovalNotPermittedError: 403,
    DomainValidationError: 400,
}

FIELD_MESSAGES = {
    "customerName": "Customer name is required.",
    "amount": "Amount must be greater than zero, with at most 2 decimal places and 12 digits before the point.",
}


def describe_validation_error(error: RequestValidationError) -> str:
    """One readable sentence for the first invalid field; never echoes internals back to the client."""
    for detail in error.errors():
        field = str(detail["loc"][-1]) if detail["loc"] else ""
        if field in FIELD_MESSAGES:
            return FIELD_MESSAGES[field]
    return "The request body is invalid."


def register_error_handlers(app: FastAPI) -> None:
    """Install the handlers that turn domain errors, HTTP errors and invalid requests into ``{"error": ...}`` responses.
    """

    def register_domain_error(error_type: type, status_code: int) -> None:
        """Register one handler that returns this domain error's message with the given status code."""

        @app.exception_handler(error_type)
        async def handler(_: Request, error: Exception):
            """Return ``{"error": <message>}`` with the mapped status code."""
            return JSONResponse({"error": str(error)}, status_code=status_code)

    for error_type, status_code in ERROR_STATUS.items():
        register_domain_error(error_type, status_code)

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, error: HTTPException):
        """Return FastAPI's own HTTP errors (such as 403 for a wrong role) in the same ``{"error": ...}`` shape."""
        return JSONResponse({"error": error.detail}, status_code=error.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, error: RequestValidationError):
        """Return 400 with one readable sentence instead of pydantic's internal detail."""
        return JSONResponse({"error": describe_validation_error(error)}, status_code=400)
