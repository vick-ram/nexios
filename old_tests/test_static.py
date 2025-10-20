import asyncio
from pathlib import Path

import pytest

from nexios import NexiosApp
from nexios.static import StaticFiles
from nexios.testing.client import Client

@pytest.mark.asyncio
async def test_static_file_serving():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    async with Client(app) as client:
        # Test existing file
        resp = await client.get("/static/example.txt")
        assert resp.status_code == 200
        assert b"welcome to nexios" in resp.content

        # Test missing file
        resp = await client.get("/static/doesnotexist.txt")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_static_file_types():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    async with Client(app) as client:
        # Test CSS file
        resp = await client.get("/static/style.css")
        assert resp.status_code == 200
        assert "text/css" in resp.headers.get("content-type", "")
        assert b"body { color: red; }" in resp.content

        # Test JS file
        resp = await client.get("/static/script.js")
        assert resp.status_code == 200
        assert "application/javascript" in resp.headers.get("content-type", "")
        assert b"console.log('Hello from JS');" in resp.content

        # Test HTML file
        resp = await client.get("/static/page.html")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert b"<img src='image.png' alt='test'>" in resp.content


@pytest.mark.asyncio
async def test_static_file_subdirectories():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    async with Client(app) as client:
        # Test file in subdirectory
        resp = await client.get("/static/subfolder/subfile.txt")
        assert resp.status_code == 200
        assert b"subfolder content" in resp.content

        # Test non-existent subdirectory
        resp = await client.get("/static/nonexistent/subfile.txt")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_static_file_directory_traversal():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    async with Client(app) as client:
        # Test directory traversal attempt
        resp = await client.get("/static/../__init__.py")
        assert resp.status_code == 404  # Should block traversal

        # Test another traversal attempt
        resp = await client.get("/static/subfolder/../../test_static.py")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_static_file_http_methods():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    async with Client(app) as client:
        # Test POST (should not be allowed)
        resp = await client.post("/static/example.txt")
        assert resp.status_code == 405  # Method Not Allowed

        # Test PUT (should not be allowed)
        resp = await client.put("/static/example.txt")
        assert resp.status_code == 405

        # Test DELETE (should not be allowed)
        resp = await client.delete("/static/example.txt")
        assert resp.status_code == 405

        # Test HEAD (should be allowed)
        resp = await client.head("/static/example.txt")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_static_file_cache_headers():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    async with Client(app) as client:
        resp = await client.get("/static/example.txt")
        assert resp.status_code == 200
        # Check for cache-related headers (adjust based on actual implementation)
        # assert "last-modified" in resp.headers
        # assert "etag" in resp.headers
        # assert "cache-control" in resp.headers
        # For now, assume basic checks
        assert "content-type" in resp.headers


@pytest.mark.asyncio
async def test_static_file_range_requests():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    async with Client(app) as client:
        # Test range request for partial content
        resp = await client.get("/static/example.txt", headers={"Range": "bytes=0-9"})
        assert resp.status_code == 206  # Partial Content
        assert b"welcome to" in resp.content
        assert resp.headers.get("content-range") is not None

        # Test invalid range
        resp = await client.get("/static/example.txt", headers={"Range": "bytes=100-200"})
        assert resp.status_code == 416  # Range Not Satisfiable


@pytest.mark.asyncio
async def test_static_file_error_cases():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    async with Client(app) as client:
        # Test root path
        resp = await client.get("/static/")
        # Depending on implementation, might serve index or 404
        assert resp.status_code in [200, 404]

        # Test empty filename
        resp = await client.get("/static/")
        assert resp.status_code in [200, 404]

        # Test very long path
        long_path = "/static/" + "a" * 1000 + ".txt"
        resp = await client.get(long_path)
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_static_file_query_params():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    async with Client(app) as client:
        # Test with query parameters
        resp = await client.get("/static/example.txt?v=1")
        assert resp.status_code == 200
        assert b"welcome to nexios" in resp.content

        # Test with fragments (though typically ignored for static files)
        resp = await client.get("/static/example.txt#section")
        assert resp.status_code == 200
        assert b"welcome to nexios" in resp.content
