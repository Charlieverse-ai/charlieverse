"""Static file serving for the React SPA."""

from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse

_WEB_DIST = Path(__file__).parent.parent.parent / "web" / "dist"


def register_routes(mcp: FastMCP) -> None:
    """Register the SPA catch-all route on the given FastMCP instance."""

    @mcp.custom_route("/{path:path}", methods=["GET"])
    async def serve_spa(request: Request):
        """Serve the React SPA — static files + index.html fallback."""
        path = request.path_params.get("path", "")

        if path.startswith("api/"):
            return JSONResponse({"error": "Not found"}, status_code=404)

        file_path = _WEB_DIST / path
        if file_path.is_file():
            return FileResponse(file_path)

        index = _WEB_DIST / "index.html"
        if index.is_file():
            return FileResponse(index)

        return PlainTextResponse("Web UI not built. Run: cd web && npm run build", status_code=404)
