"""
breathquest_core/phone_provider.py — SMS-provider abstraction.

Backed by Azure Communication Services (ACS) SMS, matching Azure hosting.
Mirrors services/email.py's send_otp_email pattern -- when
AZURE_COMMUNICATION_CONNECTION_STRING / AZURE_COMMUNICATION_FROM_NUMBER
aren't set (dev/local, or credentials not added yet), falls back to
logging the code instead of a real send, rather than a silent no-op or
a fake success.

verify.py only depends on the PhoneProvider interface (get_phone_provider()
().send_otp_sms(phone, code)), so nothing there needs to change when
credentials are added later.
"""

import logging

from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger("uvicorn.error")


class PhoneProvider:
    async def send_otp_sms(self, phone: str, code: str) -> None:
        raise NotImplementedError


class AzureCommunicationPhoneProvider(PhoneProvider):
    """Real SMS dispatch via Azure Communication Services."""

    async def send_otp_sms(self, phone: str, code: str) -> None:
        # Imported lazily so azure-communication-sms is only required
        # when this path actually runs, not at module import time --
        # keeps `from app.breathquest_core.phone_provider import
        # get_phone_provider` working even before the package is
        # installed, in envs that only ever hit the dev fallback below.
        from azure.communication.sms import SmsClient
        from azure.core.exceptions import HttpResponseError

        client = SmsClient.from_connection_string(settings.AZURE_COMMUNICATION_CONNECTION_STRING)
        try:
            results = client.send(
                from_=settings.AZURE_COMMUNICATION_FROM_NUMBER,
                to=[phone],
                message=f"Your verification code is: {code}. This code expires in 10 minutes.",
            )
            result = results[0] if isinstance(results, list) else results
            if not getattr(result, "successful", True):
                raise HttpResponseError(message=getattr(result, "error_message", "unknown ACS error"))
        except HttpResponseError as e:
            logger.error(f"ACS SMS send failed for {phone}: {e}")
            raise HTTPException(
                status_code=502,
                detail="Could not send verification SMS — please try again shortly.",
            )


class DevLoggingPhoneProvider(PhoneProvider):
    """ACS isn't configured yet (dev/local, or credentials not added) --
    log the code instead of a real send. Mirrors send_otp_email's
    SMTP-unconfigured branch exactly: still requires
    /verify/phone/confirm with the correct code, it's just read from the
    console instead of a text until credentials are set."""

    async def send_otp_sms(self, phone: str, code: str) -> None:
        logger.warning(
            "\n"
            "==================== DEV MODE: ACS NOT CONFIGURED ====================\n"
            f"  OTP code for {phone}: {code}\n"
            "  (Set AZURE_COMMUNICATION_CONNECTION_STRING/AZURE_COMMUNICATION_FROM_NUMBER in .env to send real texts)\n"
            "========================================================================"
        )


def get_phone_provider() -> PhoneProvider:
    if settings.AZURE_COMMUNICATION_CONNECTION_STRING and settings.AZURE_COMMUNICATION_FROM_NUMBER:
        return AzureCommunicationPhoneProvider()
    return DevLoggingPhoneProvider()
