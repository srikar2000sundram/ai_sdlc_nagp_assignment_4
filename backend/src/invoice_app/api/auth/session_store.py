"""In-memory sign-in sessions keyed by an opaque bearer token. Tokens do not expire (known limit, review finding F11).
"""

import secrets
import threading
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class UserSession:
    """Who is signed in: a username and the role they signed in with."""

    username: str
    role: str


class SessionStore:
    """Keeps signed-in sessions in memory, keyed by an opaque bearer token."""

    def __init__(self) -> None:
        """Create an empty, thread-safe store."""
        self._lock = threading.Lock()
        self._sessions: dict[str, UserSession] = {}

    def create(self, session: UserSession) -> str:
        """Store the session and return a new random token for it."""
        # 128 random bits: unguessable, and the token itself carries no information about the user.
        token = secrets.token_hex(16).upper()
        with self._lock:
            self._sessions[token] = session
        return token

    def get(self, token: Optional[str]) -> Optional[UserSession]:
        """Return the session for a token, or ``None`` for a missing or unknown token."""
        if token is None:
            return None
        with self._lock:
            return self._sessions.get(token)

    def remove(self, token: str) -> None:
        """Forget a token (sign out). Unknown tokens are ignored."""
        with self._lock:
            self._sessions.pop(token, None)
