import os
from pathlib import Path
from typing import List, Optional, Union

from nexios.http import Request, Response
from nexios.routing import BaseRouter
from nexios.types import Receive, Scope, Send


class StaticFiles(BaseRouter):
    def __init__(
        self,
        directory: Optional[Union[str, Path]] = None,
        directories: Optional[List[Union[str, Path]]] = None,
    ):
        if not directories:
            directories = [directory] if directory else []
        self.directories = [self._ensure_directory(d) for d in directories or []]

    def _ensure_directory(self, path: Union[str, Path]) -> Path:
        """Ensure directory exists and return resolved Path"""
        directory = Path(path).resolve()
        if not directory.exists():
            os.makedirs(directory, exist_ok=True)
        if not directory.is_dir():
            raise ValueError(f"{directory} is not a directory")
        return directory

    def _is_safe_path(self, path: Path) -> bool:
        """Check if the path is safe to serve"""
        try:
            full_path = path.resolve()
            return any(
                str(full_path).startswith(str(directory))
                for directory in self.directories
            )
        except (ValueError, RuntimeError):
            return False

    async def _handle(self, request: Request, response: Response):
        path = request.scope.get("path", "").lstrip("/")
        if request.method != "GET":
            return response.json("Method not allowed", status_code=405)
        for directory in self.directories:
            try:
                file_path = (directory / path).resolve()
                if self._is_safe_path(file_path) and file_path.is_file():
                    return response.file(
                        str(file_path), content_disposition_type="inline"
                    )
            except (ValueError, RuntimeError):
                continue

        return response.json("Resource not found", status_code=404)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        request = Request(scope, receive)
        response = Response(request)
        await self._handle(request, response)
        result = response.get_response()
        if result is not None:
            response = result
        await response(scope, receive, send)
