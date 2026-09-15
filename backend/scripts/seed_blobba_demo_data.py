"""
scripts/seed_blobba_demo_data.py — Populate demo data across all games for
patient "blobba" so the Progress overall summary, Orpheus, Flashcards,
Chime, and AgentInsight (breathquest/chime/voicehurdlerace) can actually
be exercised end-to-end instead of tested against an all-zero patient.

Run from backend/:
    PYTHONPATH=. python3 scripts/seed_blobba_demo_data.py

Idempotency: NOT idempotent for GameSession/VoiceHurdleRaceSession/
VaakMirrorSession/FlashcardAttempt/Chime events -- re-running adds more
rows on top of any existing ones. The assessment-Patient link IS
idempotent (skips creating a new one if blobba already has
assessment_patient_id set). If you need a clean slate, delete rows for
blobba's patient.id from breathquest_game_sessions,
breathquest_voicehurdlerace_sessions, vaakmirror_sessions (+ its attempts
cascade), flashcard_attempts, flashcard_phoneme_mastery, and the Chime
SQLite DB before re-running.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.patient import Patient
from app.models.breathquest_models import BreathQuestPatient, GameSession, LevelID, SessionStatus
from app.models.voicehurdlerace_models import VoiceHurdleRaceSession
from app.models.vaakmirror_models import VaakMirrorSession, Attempt, GameName, AttemptOutcome
from app.models.flashcards_models import FlashcardAttempt, PhonemeMastery
from app.retraining import data_store as chime_data_store

CHIME_DB_PATH = chime_data_store.DEFAULT_DB_PATH


def tznow():
    return datetime.now(timezone.utc)


async def main():
    async with AsyncSessionLocal() as db:
        # 1. Find blobba
        result = await db.execute(
            select(BreathQuestPatient).where(BreathQuestPatient.first_name == "blobba")
        )
        patient = result.scalars().first()
        if not patient:
            print("Could not find a BreathQuestPatient named 'blobba' -- aborting.")
            return
        print(f"Found blobba: id={patient.id}, therapist_id={patient.therapist_id}, "
              f"assessment_patient_id={patient.assessment_patient_id}")

        # 2. Link an assessment Patient row if not already linked
        if patient.assessment_patient_id:
            print("Already linked to an assessment Patient row, reusing it.")
        else:
            assessment_patient = Patient(
                id=uuid.uuid4(),
                name=patient.first_name,
                age=patient.age or 6,
                diagnosis="Articulation delay (demo data)",
                registered_therapist_id=patient.therapist_id,
                is_active=True,
                created_at=datetime.utcnow(),  # naive -- this table's column is untyped TIMESTAMP
            )
            db.add(assessment_patient)
            await db.flush()
            patient.assessment_patient_id = assessment_patient.id
            patient.assessment_completed = True
            patient.assessment_completed_at = tznow()
            print(f"Created + linked new assessment Patient row: id={assessment_patient.id}")

        # 3. BreathQuest GameSessions across 4 levels, 2 attempts each
        bq_levels = [LevelID.pinwheel, LevelID.float_rider, LevelID.candle, LevelID.balloon]
        for i, level in enumerate(bq_levels):
            for attempt in range(2):
                started = tznow() - timedelta(days=(len(bq_levels) - i) * 2, hours=attempt)
                db.add(GameSession(
                    patient_id=patient.id,
                    level_id=level,
                    started_at=started,
                    ended_at=started + timedelta(minutes=3),
                    duration_seconds=180.0,
                    status=SessionStatus.completed,
                    stars_earned=2 + (attempt % 2),
                    completed=True,
                    avg_breath_strength=0.6 + 0.05 * attempt,
                    max_breath_strength=0.85,
                    breath_consistency=0.7,
                    total_puffs=12,
                    lives_lost=1,
                ))
        print(f"Added {len(bq_levels) * 2} BreathQuest sessions.")

        # 4. Voice Hurdle Race sessions, 2 levels x 2 attempts
        vhr_levels = [(1, "Level 1: Blip's Green Plains"), (2, "Level 2: Zog's Circuit Desert")]
        for i, (lvl_id, lvl_name) in enumerate(vhr_levels):
            for attempt in range(2):
                db.add(VoiceHurdleRaceSession(
                    patient_id=patient.id,
                    level_id=lvl_id,
                    level_name=lvl_name,
                    score=800 + attempt * 50,
                    time_remaining=12.5,
                    pitch_accuracy=70.0 + attempt * 5,
                    loudness_accuracy=65.0 + attempt * 5,
                    stars=2,
                    created_at=tznow() - timedelta(days=(len(vhr_levels) - i), hours=attempt),
                ))
        print(f"Added {len(vhr_levels) * 2} Voice Hurdle Race sessions.")

        # 5. Orpheus (VaakMirror): 3 games x 4 sound attempts each
        sounds = ["r", "s", "th", "l"]
        for i, game in enumerate([GameName.mirror_mirror, GameName.tongue_tamer, GameName.lip_sync_hero]):
            vm_started = tznow() - timedelta(days=3 - i)
            vm_session = VaakMirrorSession(
                patient_id=str(patient.id),
                game=game,
                started_at=vm_started,
                ended_at=vm_started + timedelta(minutes=5),
            )
            db.add(vm_session)
            await db.flush()
            for j, sound in enumerate(sounds):
                outcome = AttemptOutcome.passed if j % 2 == 0 else AttemptOutcome.missed
                db.add(Attempt(
                    session_id=vm_session.id,
                    sound_id=sound,
                    place="alveolar",
                    manner="fricative",
                    voicing="voiced",
                    outcome=outcome,
                    score=0.8 if outcome == AttemptOutcome.passed else 0.35,
                    created_at=vm_started + timedelta(seconds=j * 20),
                ))
        print("Added 3 Orpheus sessions with 4 attempts each.")

        # 6. Flashcards: 4 phonemes x 5 attempts each, plus the mastery rows
        phonemes = ["r", "s", "l", "th"]
        words_by_phoneme = {"r": "rocket", "s": "sun", "l": "lion", "th": "thumb"}
        for i, ph in enumerate(phonemes):
            correct_count = 0
            attempts_count = 5
            for attempt_n in range(1, attempts_count + 1):
                correct = attempt_n % 2 == 0
                if correct:
                    correct_count += 1
                db.add(FlashcardAttempt(
                    patient_id=patient.id,
                    session_id=f"demo-session-{i}",
                    theme_id="animals",
                    target_word=words_by_phoneme[ph],
                    character="Blobba",
                    language="english",
                    transcript=words_by_phoneme[ph],
                    phoneme_matches=[{"expected": ph, "detected": ph if correct else "x", "correct": correct}],
                    accuracy=1.0 if correct else 0.0,
                    composite_score=90.0 if correct else 40.0,
                    attempt_number=attempt_n,
                    repeat_needed=not correct,
                    created_at=tznow() - timedelta(days=(len(phonemes) - i), hours=attempt_n),
                ))
            existing_pm = (await db.execute(
                select(PhonemeMastery).where(
                    PhonemeMastery.patient_id == patient.id,
                    PhonemeMastery.phoneme == ph,
                )
            )).scalar_one_or_none()
            if existing_pm:
                existing_pm.attempts_count += attempts_count
                existing_pm.correct_count += correct_count
                existing_pm.accuracy = round(100 * existing_pm.correct_count / existing_pm.attempts_count, 1)
                existing_pm.last_word = words_by_phoneme[ph]
                existing_pm.last_practiced_at = tznow() - timedelta(days=1)
                # keep the original first_practiced_at
            else:
                db.add(PhonemeMastery(
                    patient_id=patient.id,
                    phoneme=ph,
                    attempts_count=attempts_count,
                    correct_count=correct_count,
                    accuracy=round(100 * correct_count / attempts_count, 1),
                    last_word=words_by_phoneme[ph],
                    first_practiced_at=tznow() - timedelta(days=len(phonemes) - i),
                    last_practiced_at=tznow() - timedelta(days=1),
                ))
        print(f"Added {len(phonemes) * 5} Flashcards attempts + {len(phonemes)} PhonemeMastery rows.")

        await db.commit()
        print("Committed Postgres rows.")
        patient_id_str = str(patient.id)

    # 7. Chime events -- separate SQLite DB, synchronous API, timestamps
    # are always "now" (add_event has no custom-timestamp param).
    chime_levels = ["aa", "oo", "ma", "fa"]
    for level in chime_levels:
        for attempt in range(1, 4):
            chime_data_store.add_event(
                child_id=patient_id_str,
                level_id=level,
                attempt_number=attempt,
                score=0.5 + 0.15 * attempt,
                is_valid_attempt=attempt % 2 == 0,
                policy_used="tabular_q",
                recommended_action="hold",
                recommendation_message="Steady progress on this sound.",
                db_path=CHIME_DB_PATH,
            )
    print(f"Added {len(chime_levels) * 3} Chime events.")

    # 8. Verification read-back
    print("\n--- Verification ---")
    async with AsyncSessionLocal() as db:
        from sqlalchemy import func
        bq_count = (await db.execute(
            select(func.count(GameSession.id)).where(GameSession.patient_id == patient.id)
        )).scalar()
        vhr_count = (await db.execute(
            select(func.count(VoiceHurdleRaceSession.id)).where(VoiceHurdleRaceSession.patient_id == patient.id)
        )).scalar()
        vm_count = (await db.execute(
            select(func.count(VaakMirrorSession.id)).where(VaakMirrorSession.patient_id == patient_id_str)
        )).scalar()
        fc_count = (await db.execute(
            select(func.count(FlashcardAttempt.id)).where(FlashcardAttempt.patient_id == patient.id)
        )).scalar()
        pm_count = (await db.execute(
            select(func.count(PhonemeMastery.id)).where(PhonemeMastery.patient_id == patient.id)
        )).scalar()
    chime_count = chime_data_store.count_events(child_id=patient_id_str, db_path=CHIME_DB_PATH)

    print(f"GameSession (BreathQuest):      {bq_count}")
    print(f"VoiceHurdleRaceSession:         {vhr_count}")
    print(f"VaakMirrorSession (Orpheus):    {vm_count}")
    print(f"FlashcardAttempt:               {fc_count}")
    print(f"PhonemeMastery rows:            {pm_count}")
    print(f"Chime events:                   {chime_count}")
    print(f"\nblobba's patient.id: {patient_id_str}")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
