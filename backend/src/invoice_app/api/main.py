"""Composition root: the one place that chooses concrete implementations and wires them together."""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI

from invoice_app.domain.approval_service import ApprovalDecisions, ApprovalService
from invoice_app.domain.repository import InvoiceRepository

from .auth.middleware import install_session_middleware
from .auth.session_store import SessionStore
from .auth.user_directory import DemoUserDirectory, UserDirectory
from .error_handling import register_error_handlers
from .in_memory_repository import InMemoryInvoiceRepository
from .routers import approvals, auth, invoices
from .static_ui import RevalidatedStaticFiles

WWWROOT = Path(__file__).parent / "wwwroot"


def create_app(
    repository: Optional[InvoiceRepository] = None,
    users: Optional[UserDirectory] = None,
    policy: Optional[ApprovalDecisions] = None,
) -> FastAPI:
    """Builds the app. Every collaborator can be replaced by passing another implementation; defaults suit the demo."""
    app = FastAPI(title="Invoice Approvals")
    app.state.sessions = SessionStore()
    app.state.repository = repository if repository is not None else InMemoryInvoiceRepository()
    app.state.users = users if users is not None else DemoUserDirectory()
    app.state.approvals = ApprovalService(app.state.repository, policy)

    install_session_middleware(app)
    register_error_handlers(app)

    app.include_router(auth.router)
    app.include_router(invoices.router)
    app.include_router(approvals.router)
    app.mount("/", RevalidatedStaticFiles(directory=WWWROOT, html=True), name="ui")
    return app


app = create_app()
