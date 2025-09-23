from __future__ import annotations
import json
from datetime import datetime
from typing import Iterable  # ← removed Optional


from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, PlainTextResponse
from pydantic_settings import BaseSettings


from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, select, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from starlette.concurrency import run_in_threadpool


# ---------------------------
# Settings (reads .env)
# ---------------------------
class Settings(BaseSettings):
    APP_NAME: str = "Gmail Inbox Cleaner"
    ENV: str = "dev"
    SECRET_KEY: str = "dev_secret_change_me"
    BASE_URL: str = "http://localhost:8000"
    OWNER_EMAIL: str

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    GOOGLE_SCOPES: str = "gmail.readonly"  # keep read-only for Part 1

    DATABASE_URL: str = "sqlite+aiosqlite:///./data.db"

    class Config:
        env_file = ".env"


settings = Settings()

# ---------------------------
# Database (async SQLAlchemy)
# ---------------------------
Base = declarative_base()
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    id = Column(Integer, primary_key=True)
    owner_email = Column(String(320), unique=True, index=True, nullable=False)
    token_json = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Sender(Base):
    __tablename__ = "senders"
    id = Column(Integer, primary_key=True)
    email = Column(String(320), unique=True, index=True, nullable=False)
    unread_count = Column(Integer, default=0)
    read_count = Column(Integer, default=0)
    has_list_unsub = Column(Boolean, default=False)
    list_unsub_mailto = Column(Text, nullable=True)
    list_unsub_http = Column(Text, nullable=True)
    first_seen_ts = Column(DateTime, default=datetime.utcnow)
    last_seen_ts = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    gmail_id = Column(String(64), unique=True, index=True, nullable=False)
    thread_id = Column(String(64), index=True)
    sender_email = Column(
        String(320), index=True
    )  # simplify Part 1: store email, not FK
    internal_ts = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)


# ---------------------------
# FastAPI app
# ---------------------------
app = FastAPI(title=settings.APP_NAME)


@app.on_event("startup")
async def startup_create_tables():
    # auto-create tables for Part 1 (we'll add Alembic later)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
def root():
    return {"app": settings.APP_NAME, "owner": settings.OWNER_EMAIL}


# ---------------------------
# Gmail helpers
# ---------------------------
def build_flow(scopes: Iterable[str]):
    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=list(scopes),
    )


async def gmail_service(db: AsyncSession):
    row = (
        await db.execute(
            select(OAuthToken).where(OAuthToken.owner_email == settings.OWNER_EMAIL)
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(400, "No Gmail credentials yet. Visit /oauth/google first.")
    creds = Credentials.from_authorized_user_info(json.loads(row.token_json))
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def parse_sender(from_header: str) -> str:
    import re

    # Try to extract email inside <>
    m = re.search(r"<([^>]+)>", from_header or "")
    email = (m.group(1) if m else (from_header or "").split()[-1]).strip().lower()
    # normalize plus addressing
    if "@" in email:
        local, domain = email.split("@", 1)
        if "+" in local:
            local = local.split("+", 1)[0]
        email = f"{local}@{domain}"
    return email


# ---------------------------
# Scanner (read-only, Part 1)
# ---------------------------
@app.post("/jobs/scan")
async def job_scan(
    days: int = 30,  # scan recent mail only (change in /docs if you want)
    limit: int = 100,  # stop after N messages (quick test)
    db: AsyncSession = Depends(get_session),
):
    svc = await gmail_service(db)
    q = f"in:inbox -is:read newer_than:{days}d"
    page_token = None
    total = 0

    while True:
        # Fetch one page, but cap to remaining budget (limit - total)
        page_size = min(200, max(1, limit - total))
        resp = await run_in_threadpool(
            lambda: svc.users()
            .messages()
            .list(userId="me", q=q, maxResults=page_size, pageToken=page_token)
            .execute()
        )
        msgs = resp.get("messages", [])
        if not msgs:
            break

        for m in msgs:
            # Get metadata in the thread pool (Google client is sync)
            meta = await run_in_threadpool(
                lambda m_id=m["id"]: svc.users()
                .messages()
                .get(
                    userId="me",
                    id=m_id,
                    format="metadata",
                    metadataHeaders=[
                        "From",
                        "List-Unsubscribe",
                        "List-Unsubscribe-Post",
                    ],
                )
                .execute()
            )
            headers = {
                h["name"].lower(): h["value"]
                for h in meta.get("payload", {}).get("headers", [])
            }
            sender_email = parse_sender(headers.get("from", ""))

            # Upsert sender
            srow = (
                await db.execute(select(Sender).where(Sender.email == sender_email))
            ).scalar_one_or_none()
            if not srow:
                srow = Sender(email=sender_email, unread_count=0, read_count=0)
                db.add(srow)
            srow.unread_count += 1
            srow.last_seen_ts = datetime.utcnow()

            lu = headers.get("list-unsubscribe")
            if lu:
                srow.has_list_unsub = True
                if "<http" in lu:
                    srow.list_unsub_http = lu
                if "<mailto" in lu:
                    srow.list_unsub_mailto = lu

            # Save message if new
            existing = (
                await db.execute(select(Message).where(Message.gmail_id == m["id"]))
            ).scalar_one_or_none()
            if not existing:
                db.add(
                    Message(
                        gmail_id=m["id"],
                        thread_id=meta.get("threadId"),
                        sender_email=sender_email,
                        is_read=False,
                    )
                )

            total += 1
            if total % 20 == 0:
                print(f"[scan] processed {total} messages…")
            if total >= limit:
                await db.commit()
                return {
                    "status": "ok",
                    "messages_processed": total,
                    "note": "limit reached",
                }

        await db.commit()
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return {"status": "ok", "messages_processed": total}


# ---------------------------
# Quick metrics (for sanity check)
# ---------------------------
@app.get("/metrics")
async def metrics(db: AsyncSession = Depends(get_session)):
    total_senders = (
        await db.execute(select(func.count()).select_from(Sender))
    ).scalar_one()
    total_msgs = (
        await db.execute(select(func.count()).select_from(Message))
    ).scalar_one()
    top = (
        await db.execute(
            select(Sender.email, Sender.unread_count)
            .order_by(Sender.unread_count.desc())
            .limit(10)
        )
    ).all()
    return {
        "senders": total_senders,
        "messages": total_msgs,
        "top_unread_senders": [{"email": e, "unread": u or 0} for e, u in top],
    }


def _build_flow(scopes):
    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=list(scopes),
    )


# REPLACE your existing callback with this:
@app.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    try:
        if error:
            return PlainTextResponse(
                f"OAuth error from Google: {error}", status_code=400
            )

        if not code:
            return PlainTextResponse("Missing 'code' in callback.", status_code=400)

        scopes = [s.strip() for s in settings.GOOGLE_SCOPES.split(",") if s.strip()]
        flow = build_flow(scopes=scopes)  # or _build_flow if that's your helper
        flow.fetch_token(code=code)
        creds: Credentials = flow.credentials

        # TODO: persist creds using `db`
        return RedirectResponse(url="/connected")

    except Exception as e:
        import traceback

        traceback.print_exc()
        return PlainTextResponse(
            f"OAuth callback exception: {repr(e)}",
            status_code=500,
        )


@app.get("/health")
def health():
    return {"status": "ok"}
