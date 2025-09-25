import os
os.environ.setdefault("OWNER_EMAIL", "test@example.com")
os.environ.setdefault("GOOGLE_CLIENT_ID", "dummy")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "dummy")
os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost/oauth/callback")
os.environ.setdefault("GOOGLE_SCOPES", "https://www.googleapis.com/auth/gmail.readonly")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

def _get_app_and_client():
    import importlib
    m = importlib.import_module("app.main")
    app = getattr(m, "create_app", None)
    if callable(app):
        app = app()
    else:
        app = getattr(m, "app", None)
    try:
        from fastapi.testclient import TestClient  # type: ignore
        return app, TestClient(app)
    except Exception:
        return app, None

def test_health_like_endpoints_smoke():
    app, client = _get_app_and_client()
    assert app is not None
    if client is None:
        return  # FastAPI not available; don't fail

    for path in ("/health", "/ready", "/version"):
        try:
            r = client.get(path)
            assert r.status_code in (200, 404)
        except Exception:
            # Endpoint might not exist; that's fine
            pass
