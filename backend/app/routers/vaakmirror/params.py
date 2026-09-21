"""
routers/vaakmirror/params.py -- what the Alphabet check's VaakMirror planner
decided for THIS child (graph/alphabet_graph.py, VaakMirrorPlannerAgent).

VaakMirror games call this on mount and, when has_plan is true, open on the
child's tricky sounds (focus_sounds), the planned round size and
starting complexity. Without a plan they behave exactly as before, so a child
who never did the Alphabet check sees no change.

Round size is ALSO written to the existing per-game round-size settings when
the plan is made (routers/breathquest/assessment.py), so the therapist's
existing controls keep working; the value here is the same number.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.breathquest_models import BreathQuestPatient
from app.vaakmirror_auth import get_current_patient_id

router = APIRouter(tags=["vaakmirror-params"])


class AgentParamsOut(BaseModel):
    has_plan: bool
    primary_game: Optional[str] = None
    focus_sounds: list[str] = []
    round_size: Optional[int] = None
    start_complexity: str = "single"
    summary: Optional[str] = None


@router.get("/me/params", response_model=AgentParamsOut)
async def get_my_vaakmirror_params(
    patient_id: str = Depends(get_current_patient_id),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        select(BreathQuestPatient.assessment_summary).where(BreathQuestPatient.id == patient_id)
    )).scalar_one_or_none()
    plan = ((row or {}).get("alphabet") or {}).get("plan") or {}
    params = plan.get("vaakmirror_params")
    if not plan.get("ready") or not params:
        return AgentParamsOut(has_plan=False)
    return AgentParamsOut(
        has_plan=True,
        primary_game=params.get("primary_game"),
        focus_sounds=[s for s in params.get("focus_sounds", []) if isinstance(s, str)],
        round_size=params.get("round_size"),
        start_complexity=params.get("start_complexity") or "single",
        summary=plan.get("summary"),
    )
