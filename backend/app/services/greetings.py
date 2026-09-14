"""
services/greetings.py — Daily greeting shown to kids on login (GamePicker)
and on MyAccount: a festival wish on days the `holidays` library marks as an
Indian festival/observance, or an encouraging line on any other day.

Dates are computed in IST (Asia/Kolkata), not server-local time -- this is
an India-specific product, and a server running in UTC would otherwise
flip "today" several hours before/after the actual Indian calendar day,
showing yesterday's or tomorrow's festival at the wrong moment.

Same no-clinical-language, kid-safe framing as kid_progress.py: a festival
name and a warm line, nothing else.
"""
from datetime import datetime, timedelta
from functools import lru_cache
from statistics import mean
from zoneinfo import ZoneInfo
import hashlib

import holidays
from sqlalchemy import select, func

from app.models.breathquest_models import GameSession
from app.models.voicehurdlerace_models import VoiceHurdleRaceSession
from app.models.vaakmirror_models import VaakMirrorSession
from app.retraining import data_store as chime_data_store
import asyncio

IST = ZoneInfo("Asia/Kolkata")

# All four of the `holidays` library's India categories -- national
# (public/government) holidays plus the optional/religious observance
# calendars -- so this covers festivals across communities (Hindu, Muslim,
# Sikh, Christian, Parsi, regional) rather than just the government-
# gazetted subset. Confirmed against 2026: correctly includes Diwali, Holi,
# Eid-ul-Fitr/Bakrid, Christmas, Pongal/Makar Sankranti, Onam, Navratri/
# Dussehra, Raksha Bandhan, Ganesh Chaturthi, Guru Nanak Jayanti, etc.,
# including the lunar/regional ones whose dates shift every year.
_CATEGORIES = ("government", "optional", "optional_women", "public")

MOTIVATIONAL_MESSAGES = [
    "You're doing amazing — keep it up! 🌟",
    "Every practice session makes you stronger! 💪",
    "Ready for some fun today? 🎮",
    "You've got this! 🚀",
    "Small steps every day add up to big wins! ⭐",
    "Your buddy's excited to play with you today! 🤖",
    "Keep going — you're getting better every time! 🌈",
    "Today's a great day to earn some stars! ⭐",
]


@lru_cache(maxsize=8)
def _year_holidays(year: int):
    # Cached per year -- holidays.country_holidays() builds the whole
    # year's calendar up front, no reason to redo that on every request.
    return holidays.country_holidays("IN", years=[year], categories=_CATEGORIES)


def _friendly_name(raw: str) -> str:
    # The library joins same-day overlaps with "; " (e.g. Jan 14, 2026:
    # "Magh Bihu; Makar Sankranti; Pongal") -- re-joined here as a normal
    # "A, B & C" list rather than exposing that internal separator verbatim
    # in a kid-facing message.
    parts = raw.split("; ")
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " & " + parts[-1]


def get_daily_greeting(seed_key: str) -> dict:
    """seed_key -- something stable per-patient (e.g. the patient id) so the
    motivational line stays the same across requests today (no flip-flopping
    on a page reload) but still varies kid-to-kid and day-to-day. Not
    Python's built-in hash(): that's randomized per-process (PYTHONHASHSEED)
    unless disabled, so it wouldn't even stay stable across two requests to
    the same running server, let alone a restart."""
    today = datetime.now(IST).date()
    festival = _year_holidays(today.year).get(today)
    if festival:
        return {
            "kind": "festival",
            "message": f"Happy {_friendly_name(festival)}! 🎉",
        }

    digest = hashlib.md5(str(seed_key).encode()).hexdigest()
    idx = (today.toordinal() + int(digest, 16)) % len(MOTIVATIONAL_MESSAGES)
    return {"kind": "motivational", "message": MOTIVATIONAL_MESSAGES[idx]}


async def get_smart_greeting(patient_id, db) -> dict:
    """Data-aware upgrade of get_daily_greeting: same festival-first
    priority, but the non-festival branch is now a real signal from the
    kid's own BreathQuest history (current streak, or recent improvement)
    instead of a pure day+id hash rotation -- when that history exists.
    Falls back to the original hash-rotation message for brand-new kids
    with no sessions yet, so the greeting never sounds hollow or claims
    progress that isn't real.
    """
    today = datetime.now(IST).date()
    festival = _year_holidays(today.year).get(today)
    if festival:
        return {"kind": "festival", "message": f"Happy {_friendly_name(festival)}! \U0001F389"}

    # Streak: consecutive days (including today) with >=1 session in ANY
    # game -- BreathQuest, VoiceHurdleRace, VaakMirror, or Chime -- walking
    # backward from today. kid_progress.py's own streak only counts
    # BreathQuest; that undercounts a kid who plays other games daily but
    # skips BreathQuest, which would wrongly show "new" instead of a real
    # streak. This mirrors get_my_progress's games_played_this_week logic
    # (which does combine all four sources) applied to the streak instead.
    bq_dates = (await db.execute(
        select(func.date(GameSession.started_at)).where(GameSession.patient_id == patient_id).distinct()
    )).all()
    vhr_dates = (await db.execute(
        select(func.date(VoiceHurdleRaceSession.created_at)).where(VoiceHurdleRaceSession.patient_id == patient_id).distinct()
    )).all()
    # VaakMirrorSession.patient_id is a plain String column (see
    # kid_progress.py's own note on this) -- str() the UUID to match.
    vm_dates = (await db.execute(
        select(func.date(VaakMirrorSession.started_at)).where(VaakMirrorSession.patient_id == str(patient_id)).distinct()
    )).all()
    # Chime is sync SQLite I/O via data_store.get_events -- threaded off
    # per the same async-safety rule as kid_progress.py's chime queries.
    chime_events = await asyncio.to_thread(chime_data_store.get_events, child_id=patient_id)

    played_dates = {str(row[0]) for row in bq_dates}
    played_dates |= {str(row[0]) for row in vhr_dates}
    played_dates |= {str(row[0]) for row in vm_dates}
    played_dates |= {
        e["timestamp"].date().isoformat()
        for e in chime_events
        if e.get("timestamp") is not None
    }
    streak = 0
    cursor = today
    while cursor.isoformat() in played_dates:
        streak += 1
        cursor -= timedelta(days=1)

    if streak >= 2:
        return {
            "kind": "streak",
            "message": f"\U0001F525 {streak}-day streak! You're on fire, keep it going!",
        }

    # Improvement trend: average stars of the most recent 3 completed
    # sessions vs the 3 before that. Only fires with enough history to
    # mean something, and only when genuinely improving.
    stars_rows = (await db.execute(
        select(GameSession.stars_earned)
        .where(GameSession.patient_id == patient_id, GameSession.completed == True)
        .order_by(GameSession.started_at.desc())
        .limit(6)
    )).all()
    stars = [r[0] for r in stars_rows if r[0] is not None]
    if len(stars) >= 4:
        recent, earlier = stars[:3], stars[3:6]
        if earlier and mean(recent) > mean(earlier):
            return {
                "kind": "improving",
                "message": "\U0001F4C8 You're doing better every time you play -- awesome progress!",
            }

    if not played_dates:
        return {"kind": "new", "message": "\U0001F31F Ready for your very first adventure today?"}

    digest = hashlib.md5(str(patient_id).encode()).hexdigest()
    idx = (today.toordinal() + int(digest, 16)) % len(MOTIVATIONAL_MESSAGES)
    return {"kind": "motivational", "message": MOTIVATIONAL_MESSAGES[idx]}
