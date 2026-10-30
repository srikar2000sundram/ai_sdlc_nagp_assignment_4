"""Serves the web UI files so a browser always asks again instead of showing an old copy."""

from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope


class RevalidatedStaticFiles(StaticFiles):
    """StaticFiles that tells browsers to re-check every file (``Cache-Control: no-cache``).

    Without it a browser may keep using an old ``styles.css`` or ``app.js`` after they change. The files are small and
    ETags still let the browser skip the download when nothing changed.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        """Return the normal response with the no-cache header added."""
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response
