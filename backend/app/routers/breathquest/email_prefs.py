"""
routers/breathquest/email_prefs.py — public unsubscribe/resubscribe links
for the weekly progress/nudge email footer (see app/services/email.py and
app/breathquest_core/weekly_update.py). Deliberately no auth: these are
clicked straight out of a mail client, where there's no parent session to
check against -- the signed token in the URL (see
security.create_unsubscribe_token) is what authorizes the change, the
same way a password-reset link works.

Returns plain HTML rather than JSON since a browser opens these links
directly, not the frontend SPA or an API client.
"""

from fastapi import APIRouter, Query, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.breathquest_models import BreathQuestPatient
from app.breathquest_core.security import decode_unsubscribe_token

router = APIRouter(prefix="/email", tags=["Email preferences"])


def _page(heading: str, body: str) -> HTMLResponse:
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{heading}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; background: #12142E; color: #fff;
          display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }}
  .card {{ max-width: 420px; padding: 32px; text-align: center; }}
  h1 {{ font-size: 22px; margin-bottom: 12px; }}
  p {{ color: rgba(255,255,255,0.6); line-height: 1.5; }}
</style></head>
<body><div class="card"><h1>{heading}</h1><p>{body}</p></div></body></html>""")


async def _resolve_patient(token: str, db: AsyncSession) -> BreathQuestPatient | None:
    patient_id = decode_unsubscribe_token(token)
    if not patient_id:
        return None
    result = await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.id == patient_id))
    return result.scalar_one_or_none()


@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    patient = await _resolve_patient(token, db)
    if not patient:
        return _page("Link expired", "This unsubscribe link is no longer valid. If you're still getting emails you don't want, just reply to one and let us know.")

    patient.weekly_email_opt_out = True
    await db.commit()
    return _page("You're unsubscribed", f"You won't get any more weekly emails about {patient.first_name}'s practice. You can turn them back on any time from Settings in the parent app.")


@router.get("/resubscribe", response_class=HTMLResponse)
async def resubscribe(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    patient = await _resolve_patient(token, db)
    if not patient:
        return _page("Link expired", "This link is no longer valid. Head to Settings in the parent app to turn weekly emails back on.")

    patient.weekly_email_opt_out = False
    await db.commit()
    return _page("You're resubscribed", f"You'll get weekly emails about {patient.first_name}'s practice again.")
