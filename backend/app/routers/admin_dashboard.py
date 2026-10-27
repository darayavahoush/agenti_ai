import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_events import log_auth_event
from app.breathquest_core.login_throttle import check_throttle, record_failure, record_success
from app.breathquest_core.security import verify_password
from app.database import get_db
from app.models.admin_payments import AdminUser, AiSummary, AuthEvent, Payment

router = APIRouter(prefix="/admin", tags=["admin"])
bearer = HTTPBearer(auto_error=False)
ALGO = "HS256"


def _secret() -> str:
    s = os.getenv("ADMIN_JWT_SECRET")
    if not s:
        raise HTTPException(status_code=503, detail="Admin is not configured")
    return s


async def get_admin(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, _secret(), algorithms=[ALGO])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("scope") != "admin":
        raise HTTPException(status_code=401, detail="Invalid token")
    admin = await db.get(AdminUser, int(payload["sub"]))
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid token")
    return admin


class AdminLogin(BaseModel):
    email: str
    password: str


@router.post("/login")
async def admin_login(data: AdminLogin, request: Request, db: AsyncSession = Depends(get_db)):
    email = data.email.strip().lower()
    key = f"admin:{email}"
    throttle = await check_throttle(key, db)
    if throttle.locked:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please try again later.",
            headers={"Retry-After": str(throttle.retry_after_seconds)},
        )
    admin = (await db.execute(select(AdminUser).where(func.lower(AdminUser.email) == email))).scalar_one_or_none()
    if not admin or not verify_password(data.password, admin.password_hash):
        await record_failure(key, db)
        await db.commit()
        await log_auth_event("admin", None, False, request)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await record_success(key, db)
    await log_auth_event("admin", admin.id, True, request)
    token = jwt.encode(
        {"sub": str(admin.id), "scope": "admin", "exp": datetime.now(timezone.utc) + timedelta(hours=8)},
        _secret(), algorithm=ALGO,
    )
    return {"access_token": token, "token_type": "bearer"}


async def _collect_metrics(db: AsyncSession, days: int) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    non_admin = AuthEvent.user_type != "admin"

    day = func.date(AuthEvent.created_at)
    dau_rows = (await db.execute(
        select(day, AuthEvent.user_type, func.count(func.distinct(AuthEvent.user_id)))
        .where(AuthEvent.success.is_(True), non_admin, AuthEvent.created_at >= since)
        .group_by(day, AuthEvent.user_type).order_by(day)
    )).all()
    dau = [{"date": d.isoformat(), "user_type": t, "active_users": n} for d, t, n in dau_rows]

    login_rows = (await db.execute(
        select(AuthEvent.user_type, AuthEvent.success, func.count())
        .where(non_admin, AuthEvent.created_at >= since)
        .group_by(AuthEvent.user_type, AuthEvent.success)
    )).all()
    logins: dict = {}
    for t, ok, n in login_rows:
        logins.setdefault(t, {"success": 0, "failed": 0})["success" if ok else "failed"] = n

    pay_rows = (await db.execute(
        select(Payment.state, func.count(), func.coalesce(func.sum(Payment.amount_paise), 0))
        .where(Payment.created_at >= since).group_by(Payment.state)
    )).all()
    payments = {s: {"count": n, "amount_paise": int(a)} for s, n, a in pay_rows}
    revenue_paise = payments.get("completed", {}).get("amount_paise", 0)

    failed = (await db.execute(
        select(Payment).where(Payment.state == "failed", Payment.created_at >= since)
        .order_by(Payment.created_at.desc()).limit(20)
    )).scalars().all()
    failed_payments = [{
        "merchant_order_id": p.merchant_order_id, "owner_kind": p.owner_kind,
        "plan_type": p.plan_type, "amount_paise": p.amount_paise,
        "payment_mode": p.payment_mode, "failure_reason": p.failure_reason,
        "created_at": p.created_at.isoformat(),
    } for p in failed]

    return {
        "window_days": days,
        "daily_active_users": dau,
        "logins": logins,
        "payments_by_state": payments,
        "revenue_paise": revenue_paise,
        "revenue_inr": revenue_paise / 100,
        "failed_payments": failed_payments,
    }


@router.get("/metrics")
async def metrics(days: int = 7, admin: AdminUser = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    return await _collect_metrics(db, max(1, min(days, 90)))


def _template_summary(n: dict) -> str:
    lg = n["logins"]
    ok = sum(v.get("success", 0) for v in lg.values())
    bad = sum(v.get("failed", 0) for v in lg.values())
    pay = n["payments_by_state"]
    return (
        f"Last {n['window_days']} days: {ok} successful and {bad} failed logins. "
        f"Revenue Rs {n['revenue_inr']:.2f} from {pay.get('completed', {}).get('count', 0)} completed payments; "
        f"{pay.get('failed', {}).get('count', 0)} failed."
    )


@router.post("/summary")
async def generate_summary(days: int = 7, admin: AdminUser = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    import json
    import logging
    numbers = await _collect_metrics(db, max(1, min(days, 90)))
    text = _template_summary(numbers)
    quiet = not numbers["logins"] and not numbers["payments_by_state"]
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if not quiet and endpoint and key and deployment:
        try:
            from openai import AsyncAzureOpenAI
            client = AsyncAzureOpenAI(
                azure_endpoint=endpoint, api_key=key,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            )
            resp = await client.chat.completions.create(
                model=deployment,
                max_completion_tokens=300,
                messages=[
                    {"role": "system", "content": (
                        "You write a brief plain-language status summary for the owner of a speech-therapy app. "
                        "Use only the numbers provided; never invent figures. Mention user activity, login "
                        "failures, revenue (INR) and failed payments worth attention. Under 120 words.")},
                    {"role": "user", "content": json.dumps(numbers)},
                ],
            )
            text = (resp.choices[0].message.content or "").strip() or text
        except Exception:
            logging.getLogger(__name__).exception("AI summary failed; using template")
    row = AiSummary(text=text, input_numbers=numbers)
    db.add(row)
    await db.flush()
    return {"id": row.id, "text": text, "created_at": datetime.now(timezone.utc).isoformat()}


@router.get("/summaries")
async def list_summaries(admin: AdminUser = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(AiSummary).order_by(AiSummary.created_at.desc()).limit(10))).scalars().all()
    return [{"id": r.id, "text": r.text, "created_at": r.created_at.isoformat()} for r in rows]
