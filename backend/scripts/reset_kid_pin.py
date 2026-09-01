"""
One-off: reset one existing BreathQuestPatient's PIN to a known value so
you have a guaranteed-working set of login credentials to test with.

PINs are stored as a one-way SHA-256 hash (see breathquest_core/security.py)
-- there is no way to recover an existing PIN, only overwrite it with a new
known one. This updates pin_hash directly via the same hash_pin() the real
kid-pin-setup/register endpoints use, so the reset account logs in exactly
like any other.

Usage (defaults reset the 'testkid' duplicate at CHICK48 to PIN 1234):
    python -m scripts.reset_kid_pin
    python -m scripts.reset_kid_pin --player-code CHICK56 --pin 5678
"""
import argparse
import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.breathquest_core.security import hash_pin
from app.models.breathquest_models import BreathQuestPatient
import app.models.patient  # noqa: F401 -- registers `patients` table so the
                            # assessment_patient_id FK on BreathQuestPatient
                            # resolves at commit time; unused directly here.
import app.models.therapist  # noqa: F401 -- registers `therapists` table so the
                              # therapist_id FK on BreathQuestPatient resolves
                              # too; unused directly here.


async def main(player_code: str, pin: str):
    if not pin.isdigit() or len(pin) != 4:
        raise SystemExit(f"PIN must be exactly 4 digits, got {pin!r}")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(BreathQuestPatient).where(BreathQuestPatient.player_code == player_code.upper())
        )
        patient = result.scalar_one_or_none()
        if patient is None:
            raise SystemExit(f"No patient with player_code={player_code.upper()!r}")

        patient.pin_hash = hash_pin(pin)
        await db.commit()

        print("PIN reset. Log in at /breathquest/play with:")
        print(f"  Name or Player Code : {patient.first_name}  (or {patient.player_code})")
        print(f"  PIN                 : {pin}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--player-code", default="CHICK48", help="player_code of the account to reset (default: CHICK48, the self-registered 'testkid')")
    parser.add_argument("--pin", default="1234", help="new 4-digit PIN (default: 1234)")
    args = parser.parse_args()
    asyncio.run(main(args.player_code, args.pin))
