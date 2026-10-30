"""The demo accounts. Local, in-memory and not real credentials."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoUser:
    """A demo account: username, password and the role it signs in with."""

    username: str
    password: str
    role: str


# Demo accounts for a local, in-memory app. They are not real credentials.
DEMO_USERS: tuple[DemoUser, ...] = (
    DemoUser("demo.manager", "ChangeMe123!", "Manager"),
    DemoUser("demo.director", "ChangeMe123!", "Director"),
    DemoUser("demo.director2", "ChangeMe123!", "Director"),
    DemoUser("demo.admin", "ChangeMe123!", "Admin"),
)
