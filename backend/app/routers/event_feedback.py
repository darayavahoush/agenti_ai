"""
routers/event_feedback.py — one shared "was this score right?" thumbs
up/down endpoint for every game (BreathQuest's Chime/VoiceHurdleRace,
PhonemeQuest, VaakMirror). All of them write attempts into the same
breathquest_rl_training_events table via data_store.add_event, so
feedback keys off that table's own id rather than duplicating this
endpoint per game.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal

from app.breathquest_core.deps import get_current_patient
from app.models.breathquest_models import BreathQuestPatient
from app.retraining import data_store

router = APIRouter(tags=["event-feedback"])


class FeedbackIn(BaseModel):
    # "up"/"down" cover the simple chip (burst games, VoiceHurdleRace).
    # "too_generous"/"too_strict" are the vowel games' 3-way variant --
    # same "up" for a correct score, but a split "down" that says which
    # direction the miss went, which is what actually tells you whether
    # to widen or narrow that game's formant tolerance.
    feedback: Literal["up", "down", "too_generous", "too_strict"]


class FeedbackOut(BaseModel):
    id: int
    feedback: str
    feedback_at: str


@router.patch("/events/{event_id}/feedback", response_model=FeedbackOut)
def submit_feedback(
    event_id: int,
    body: FeedbackIn,
    patient: BreathQuestPatient = Depends(get_current_patient),
):
    updated = data_store.set_event_feedback(
        event_id=event_id,
        child_id=patient.id,
        feedback=body.feedback,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return FeedbackOut(
        id=updated.id,
        feedback=updated.feedback,
        feedback_at=updated.feedback_at.isoformat(),
    )
