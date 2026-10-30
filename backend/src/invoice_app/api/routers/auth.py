"""Sign-in and sign-out endpoints."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from ..auth.dependencies import bearer_token
from ..auth.session_store import UserSession

router = APIRouter(prefix="/api/auth")


class LoginRequest(BaseModel):
    """Body of ``POST /api/auth/login``."""

    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest, request: Request):
    """Exchange a username and password for a bearer token (401 for a wrong pair)."""
    user = request.app.state.users.authenticate(body.username, body.password)
    if user is None:
        return JSONResponse({"error": "Invalid username or password."}, status_code=401)

    token = request.app.state.sessions.create(UserSession(user.username, user.role))
    return {"token": token, "username": user.username, "role": user.role}


@router.post("/logout", status_code=204)
def logout(request: Request):
    """Forget the caller's token. Always 204."""
    token = bearer_token(request)
    if token:
        request.app.state.sessions.remove(token)
    return Response(status_code=204)
