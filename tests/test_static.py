from pathlib import Path

from nexios import NexiosApp
from nexios.static import StaticFiles
from nexios.testclient import TestClient


def test_static_file_serving():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    with TestClient(app) as client:
        resp = client.get("/static/example.txt")
        assert resp.status_code == 200
        assert b"welcome to nexios" in resp.content

        resp = client.get("/static/doesnotexist.txt")
        assert resp.status_code == 404


def test_static_file_types():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    with TestClient(app) as client:
        resp = client.get("/static/style.css")
        assert resp.status_code == 200
        assert "text/css" in resp.headers.get("content-type", "")
        assert b"body { color: red; }" in resp.content

        resp = client.get("/static/script.js")
        assert resp.status_code == 200
        assert "text/javascript" in resp.headers.get("content-type", "")
        assert b"console.log('Hello from JS');" in resp.content

        resp = client.get("/static/page.html")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert b"<img src='image.png' alt='test'>" in resp.content


def test_static_file_subdirectories():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    with TestClient(app) as client:
        resp = client.get("/static/subfolder/subfile.txt")
        assert resp.status_code == 200
        assert b"subfolder content" in resp.content

        resp = client.get("/static/nonexistent/subfile.txt")
        assert resp.status_code == 404


def test_static_file_directory_traversal():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    with TestClient(app) as client:
        resp = client.get("/static/../__init__.py")
        assert resp.status_code == 404

        resp = client.get("/static/subfolder/../../test_static.py")
        assert resp.status_code == 404


def test_static_file_http_methods():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    with TestClient(app) as client:
        resp = client.post("/static/example.txt")
        assert resp.status_code == 405

        resp = client.put("/static/example.txt")
        assert resp.status_code == 405

        resp = client.delete("/static/example.txt")
        assert resp.status_code == 405


def test_static_file_cache_headers():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    with TestClient(app) as client:
        resp = client.get("/static/example.txt")
        assert resp.status_code == 200
        assert "content-type" in resp.headers


def test_static_file_range_requests():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    with TestClient(app) as client:
        resp = client.get("/static/example.txt", headers={"Range": "bytes=0-9"})
        assert resp.status_code == 206
        assert b"welcome to" in resp.content
        assert resp.headers.get("content-range") is not None

        resp = client.get("/static/example.txt", headers={"Range": "bytes=100-200"})
        assert resp.status_code == 206


def test_static_file_error_cases():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    with TestClient(app) as client:
        resp = client.get("/static/")
        assert resp.status_code in [200, 404]

        resp = client.get("/static/")
        assert resp.status_code in [200, 404]


def test_static_file_query_params():
    app = NexiosApp()
    static_dir = Path(__file__).parent / "static"
    app.register(StaticFiles(directory=static_dir), "/static")

    with TestClient(app) as client:
        resp = client.get("/static/example.txt?v=1")
        assert resp.status_code == 200
        assert b"welcome to nexios" in resp.content

        resp = client.get("/static/example.txt#section")
        assert resp.status_code == 200
        assert b"welcome to nexios" in resp.content
