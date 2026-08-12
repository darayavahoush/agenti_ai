"""
breathquest_core/phone_provider.py — SMS-provider abstraction stub.

Mirrors billing_provider.py's pattern exactly: no Twilio/SMS provider has
been picked yet, so routers/breathquest/verify.py's phone endpoints call
this interface instead of talking to a real provider directly. This stub
returns honest 501s rather than pretending an SMS was sent.

Swap get_phone_provider's return value for a real TwilioProvider (or
similar) once a provider is chosen -- nothing in verify.py needs to
change, since it only depends on this interface. In the meantime,
request_phone_verification still creates the PhoneVerification row and
generates a real code (see verify.py) -- only the actual SMS dispatch is
stubbed, same division of "real logic, fake I/O" as billing_provider.py.
"""

from fastapi import HTTPException


class PhoneProvider:
    async def send_otp_sms(self, phone: str, code: str) -> None:
        raise NotImplementedError


class StubPhoneProvider(PhoneProvider):
    """No SMS provider is wired up yet. Explicit 501, matching
    billing_provider.py's "no fake success responses, no silent no-ops"
    stance rather than pretending a text was sent."""

    async def send_otp_sms(self, phone: str, code: str) -> None:
        raise HTTPException(
            status_code=501,
            detail="Phone verification is not set up yet -- no SMS provider is configured.",
        )


def get_phone_provider() -> PhoneProvider:
    return StubPhoneProvider()
