"""The session check applied to every API call."""

from fastapi import FastAPI, Request
from fastapi.responses import Response

from .dependencies import bearer_token


def install_session_middleware(app: FastAPI) -> None:
    """Every /api route except login needs a valid session; the session is attached to the request."""

    @app.middleware("http")
    async def require_session(request: Request, call_next):
        """Return 401 for any /api call (except login) without a valid session; otherwise attach the session to the request.
        """
        path = request.url.path
        if path.startswith("/api") and path != "/api/auth/login":
            session = request.app.state.sessions.get(bearer_token(request))
            if session is None:
                return Response(status_code=401)
            request.state.session = session
        return await call_next(request)
