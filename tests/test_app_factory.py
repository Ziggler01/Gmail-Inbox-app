import os

# Ensure env so settings load
os.environ.setdefault("OWNER_EMAIL", "test@example.com")
os.environ.setdefault("GOOGLE_CLIENT_ID", "dummy")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "dummy")
os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost/oauth/callback")
os.environ.setdefault("GOOGLE_SCOPES", "https://www.googleapis.com/auth/gmail.readonly")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

def test_app_or_factory():
    import app.main as m
    # Prefer an app factory if present (safer for tests)
    app = getattr(m, "create_app", None)
    if callable(app):
        app = app()
    else:
        app = getattr(m, "app", None)
    assert app is not None
    # Basic shape checks
    assert hasattr(app, "routes")
    assert len(getattr(app, "routes", [])) >= 0
