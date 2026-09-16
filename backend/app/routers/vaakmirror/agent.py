"""
routers/vaakmirror/agent.py — the same adaptive-difficulty agent ladder
already wired into BreathQuest (breath_agent.py), Chime (chime.py), and
VoiceHurdleRace (voicehurdlerace.py), extended to VaakMirror.

VaakMirror already logs real gameplay into the shared AgentService /
data_store via sessions.py's log_attempt (level_id = "vm_{sound_id}", one
shared level per sound across all three VaakMirror sub-games -- see that
module's docstring). This file only adds the decide()/get_status()
*endpoints* on top of that already-flowing data, the same way
breath_agent.py added them for BreathQuest's own events. Reuses sessions.py's
_agent_service instance directly (not a second AgentService(...)) so
in-memory state -- _pending_transitions, _last_decisions, _recurrent_states
-- stays consistent between a decide() call here and the next logged
attempt in sessions.py.

Patient resolution deliberately follows breath_agent.py / chime.py /
voicehurdlerace.py's pattern (BreathQuestPatient.assessment_patient_id ==
the incoming assessment-side patient_id, scoped to
BreathQuestPatient.therapist_id == therapist.id) -- NOT
vaakmirror_auth.py's assert_therapist_owns_patient/get_patient_summary
helpers dashboard.py uses. Those resolve ownership against the `patients`
table directly, then use that same raw id against
VaakMirrorSession.patient_id -- but VaakMirrorSession.patient_id actually
stores BreathQuestPatient.id (see sessions.py's create_session), not
patients.id. Mixing those two id spaces is a pre-existing issue in
dashboard.py (flagged separately, out of scope here); this module avoids
repeating it by resolving through BreathQuestPatient explicitly, the same
as every other game's agent/status route already does correctly.

`level_id` in this file's query/path params is the bare sound id (e.g.
"sh", "r"), matching soundTaxonomy.js's SOUNDS[].id on the frontend --
_vm_level_id() below adds the "vm_" prefix before touching AgentService,
the same transform sessions.py applies when logging attempts.
"""

import asyncio
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.breathquest_models import BreathQuestPatient
from app.models.therapist import Therapist
from app.deps.therapist_auth_deps import get_current_therapist
from app.vaakmirror_auth import get_current_patient_id

from app.routers.vaakmirror.sessions import _agent_service

router = APIRouter(tags=["vaakmirror-agent"])


class AgentStatusObs(BaseModel):
    success_rate: float
    difficulty: float
    frustration: float
    severity_numeric: float
    is_targeted_sound: bool


class AgentStatusOut(BaseModel):
    policy: str
    requested_policy: str
    n_events_considered: int
    downgrade_reason: Optional[str]
    obs: AgentStatusObs


class AgentDecisionOut(BaseModel):
    policy: str
    requested_policy: Optional[str] = None
    action: Literal["raise", "lower", "hold"]
    n_events_considered: int
    message: str
    downgrade_reason: Optional[str] = None


def _vm_level_id(sound_id: str) -> str:
    return f"vm_{sound_id}"


@router.get("/agent/status/{patient_id}", response_model=AgentStatusOut)
async def vaakmirror_agent_status(
    patient_id: str,
    level_id: str,
    policy: Literal["rule_based", "bandit", "tabular_q", "ppo", "recurrent_ppo"] = "tabular_q",
    therapist: Therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    patient_result = await db.execute(
        select(BreathQuestPatient).where(
            BreathQuestPatient.assessment_patient_id == patient_id,
            BreathQuestPatient.therapist_id == therapist.id,
        )
    )
    patient_row = patient_result.scalar_one_or_none()
    if not patient_row:
        raise HTTPException(status_code=404, detail="Patient not found")

    result = await asyncio.to_thread(
        _agent_service.get_status, patient_row.id, _vm_level_id(level_id), policy
    )
    return AgentStatusOut(**result)


@router.get("/agent/decide/{level_id}", response_model=AgentDecisionOut)
def vaakmirror_agent_decide(
    level_id: str,
    policy: Literal["rule_based", "bandit", "tabular_q", "ppo", "recurrent_ppo"] = "tabular_q",
    patient_id: str = Depends(get_current_patient_id),
):
    try:
        result = _agent_service.decide(patient_id, _vm_level_id(level_id), policy)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"Model not found: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AgentDecisionOut(**result)
