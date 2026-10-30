"""FastAPI dependencies for reading the caller's token and session, and for restricting endpoints by role."""

from fastapi import HTTPException, Request

from .session_store import UserSession

BEARER_PREFIX = "Bearer "


def bearer_token(request: Request) -> str | None:
    """Extract the token from an ``Authorization: Bearer <token>`` header, or ``None`` if absent."""
    header = request.headers.get("authorization", "")
    return header[len(BEARER_PREFIX):] if header.startswith(BEARER_PREFIX) else None


def current_session(request: Request) -> UserSession:
    """Return the session the middleware attached to this request."""
    return request.state.session


def require_role(*roles: str):
    """Allows the endpoint only for the listed roles; everyone else gets 403."""

    def check(request: Request) -> UserSession:
        """Raise 403 unless the request's session has one of the allowed roles."""
        # The middleware attached the session. No session, or a role that is not allowed, is refused with 403.
        session = getattr(request.state, "session", None)
        if session is None or session.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to do that.")
        return session

    return check
