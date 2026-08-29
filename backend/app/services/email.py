"""
services/email.py — sends OTP verification codes via Gmail SMTP. Deliberately
plain smtplib rather than a transactional-email SDK: this is one templated
message, low volume (login-gate OTPs, not marketing/bulk mail), so a full
provider integration would be more dependency than the job needs.

Ported 2026-08-12 from quest-games/breathquest/backend/core/email.py --
import path fixed (app.config instead of core.config), otherwise unchanged.
verify.py (the only caller) was never mounted in main.py before this because
it still had the old standalone-layout imports; see main.py's include_router
call for verify.router for the fix that made this reachable.
"""

import logging
import smtplib
import ssl
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger("uvicorn.error")


def send_otp_email(to_email: str, code: str) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        # Dev-only fallback -- mirrors AUTO_VERIFY_CONSENT's pattern of a
        # clearly-flagged temporary bypass rather than a silent one. SMTP
        # unconfigured means local/dev, not production (real deploys must
        # set these three env vars), so print the code instead of a 500.
        # This does NOT skip the OTP flow -- the frontend still requires
        # /verify/confirm with the correct code, it's just read from the
        # console instead of an inbox until a provider is wired up.
        logger.warning(
            "\n"
            "==================== DEV MODE: SMTP NOT CONFIGURED ====================\n"
            f"  OTP code for {to_email}: {code}\n"
            "  (Set SMTP_HOST/SMTP_USER/SMTP_PASSWORD in .env to send real emails)\n"
            "========================================================================"
        )
        return

    message = MIMEText(
        f"Your verification code is: {code}\n\nThis code expires in 10 minutes."
    )
    message["Subject"] = "Your verification code"
    message["From"] = settings.SMTP_USER
    message["To"] = to_email

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_USER, [to_email], message.as_string())


def send_account_reminder_email(to_email: str, player_code: str) -> None:
    """'Forgot my email' recovery -- the parent already owns this
    inbox (that's how they'll receive it), so this isn't proving
    identity, just reminding them which address is on file for a
    given player code. Same dev-fallback pattern as send_otp_email."""
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(
            "\n"
            "==================== DEV MODE: SMTP NOT CONFIGURED ====================\n"
            f"  Account reminder for player code {player_code}: {to_email}\n"
            "  (Set SMTP_HOST/SMTP_USER/SMTP_PASSWORD in .env to send real emails)\n"
            "========================================================================"
        )
        return

    message = MIMEText(
        f"Hi,\n\nSomeone (hopefully you!) asked for a reminder of the email "
        f"registered to the BreathQuest account for player code {player_code}.\n\n"
        f"That email is: {to_email}\n\n"
        f"If you didn't request this, you can safely ignore this message."
    )
    message["Subject"] = "Your BreathQuest account email"
    message["From"] = settings.SMTP_USER
    message["To"] = to_email

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_USER, [to_email], message.as_string())
def send_player_code_email(to_email: str, player_code: str) -> None:
    """'Forgot my child's player code' recovery -- the parent already
    owns this inbox (it's their login email on file), so this isn't
    proving identity, just reminding them of the player code linked
    to their account. Same dev-fallback pattern as send_otp_email."""
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(
            "\n"
            "==================== DEV MODE: SMTP NOT CONFIGURED ====================\n"
            f"  Player code reminder for {to_email}: {player_code}\n"
            "  (Set SMTP_HOST/SMTP_USER/SMTP_PASSWORD in .env to send real emails)\n"
            "========================================================================"
        )
        return

    message = MIMEText(
        f"Hi,\n\nSomeone (hopefully you!) asked for a reminder of your "
        f"child's BreathQuest player code.\n\n"
        f"Player code: {player_code}\n\n"
        f"If you didn't request this, you can safely ignore this message."
    )
    message["Subject"] = "Your child's BreathQuest player code"
    message["From"] = settings.SMTP_USER
    message["To"] = to_email

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_USER, [to_email], message.as_string())
