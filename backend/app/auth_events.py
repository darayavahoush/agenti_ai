import logging
from fastapi import Request
from app.database import AsyncSessionLocal
from app.models.admin_payments import AuthEvent

log = logging.getLogger(__name__)

async def log_auth_event(user_type: str, user_id, success: bool, request: Request | None = None) -> None:
    """Best-effort login-attempt record, written in its own session so it
    survives the request session's rollback on HTTPException. Never raises.
    For failed logins, user_id may be the attempted identifier (truncated)."""
    try:
        ip = ua = None
        if request is not None:
            fwd = request.headers.get("x-forwarded-for")
            ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else None)
            ua = (request.headers.get("user-agent") or "")[:256]
        async with AsyncSessionLocal() as s:
            s.add(AuthEvent(
                user_type=user_type,
                user_id=str(user_id)[:64] if user_id is not None else None,
                success=success, ip=(ip or None) and ip[:64], user_agent=ua,
            ))
            await s.commit()
    except Exception:
        log.exception("failed to log auth event")
