"""Where user accounts come from, behind a small contract so the login endpoint does not depend on how they are stored.
"""

from dataclasses import dataclass
from typing import Optional, Protocol

from .demo_users import DEMO_USERS, DemoUser


@dataclass(frozen=True)
class AuthenticatedUser:
    """A user who passed authentication: username and role."""

    username: str
    role: str


class UserDirectory(Protocol):
    """Who may sign in. The login endpoint depends on this, not on where the accounts are kept."""

    def authenticate(self, username: str, password: str) -> Optional[AuthenticatedUser]:
        """Return the user when the username and password match, otherwise ``None``."""


class DemoUserDirectory:
    """The fixed demo accounts. A real deployment would provide another UserDirectory without touching the router."""

    def __init__(self, users: tuple[DemoUser, ...] = DEMO_USERS) -> None:
        """Args:
            users: The accounts to accept. Defaults to the fixed demo accounts.
        """
        self._users = users

    def authenticate(self, username: str, password: str) -> Optional[AuthenticatedUser]:
        """Return the matching demo user, or ``None`` for a wrong username or password."""
        user = next((u for u in self._users if u.username == username and u.password == password), None)
        return AuthenticatedUser(user.username, user.role) if user else None
