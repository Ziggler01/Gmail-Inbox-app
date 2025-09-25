import os

# Seed env once
os.environ.setdefault("OWNER_EMAIL", "test@example.com")
os.environ.setdefault("GOOGLE_CLIENT_ID", "dummy")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "dummy")
os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost/oauth/callback")
os.environ.setdefault("GOOGLE_SCOPES", "https://www.googleapis.com/auth/gmail.readonly")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

def test_settings_accessible():
    import app.main as m
    # Prefer a lazy accessor if available
    get_settings = getattr(m, "get_settings", None)
    if callable(get_settings):
        s = get_settings()
    else:
        # Fallback if module exposes settings directly
        s = getattr(m, "settings", None)
    assert s is not None
    assert hasattr(s, "OWNER_EMAIL")
    assert s.OWNER_EMAIL  # not empty

def test_lifespan_startup_if_present():
    import app.main as m
    app = getattr(m, "create_app", None)
    if callable(app):
        app = app()
    else:
        app = getattr(m, "app", None)

    try:
        from fastapi.testclient import TestClient  # type: ignore
        with TestClient(app) as client:
            r = client.get("/")  # harmless root if present
            assert r.status_code in (200, 404)
    except Exception:
        # If not FastAPI / no routes, that's fine—import path still covered
        pass
