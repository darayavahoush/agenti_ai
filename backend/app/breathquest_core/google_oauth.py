"""breathquest_core/google_oauth.py -- server-side verification of Google
Sign-In ID tokens, shared by therapist and parent Google auth endpoints.

The frontend uses Google Identity Services to get an ID token directly
from Google (no server-side redirect/callback dance, no client secret
needed here) and sends just that token to us. We never trust it as-is --
`google.oauth2.id_token.verify_oauth2_token` cryptographically verifies
the signature against Google's published public keys and checks
expiry, then we additionally check `aud` matches our own client ID
(done inside verify_oauth2_token via the second argument) so a token
minted for a different app can't be replayed against this backend.
"""

from dataclasses import dataclass

from fastapi import HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.breathquest_core.config import get_breathquest_settings

settings = get_breathquest_settings()

# Reused across verify calls -- this just wraps a requests.Session for
# fetching Google's public certs, which google-auth itself caches
# internally based on the certs' own Cache-Control headers.
_google_request = google_requests.Request()


@dataclass
class GoogleUser:
    sub: str
    email: str
    email_verified: bool
    name: str | None


def verify_google_id_token(token: str) -> GoogleUser:
    """Verifies a Google ID token and returns the identity it asserts.
    Raises HTTPException(401) on any invalid/expired/wrong-audience
    token, and HTTPException(500) if GOOGLE_CLIENT_ID isn't configured
    (fail loud, not a silent accept-anything mode)."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google sign-in isn't configured on this server")

    try:
        payload = google_id_token.verify_oauth2_token(
            token, _google_request, settings.GOOGLE_CLIENT_ID
        )
    except ValueError:
        # Covers bad signature, expired token, wrong audience/issuer --
        # verify_oauth2_token collapses all of these into ValueError.
        raise HTTPException(status_code=401, detail="Invalid or expired Google sign-in token")

    return GoogleUser(
        sub=payload["sub"],
        email=payload.get("email", ""),
        email_verified=bool(payload.get("email_verified", False)),
        name=payload.get("name"),
    )
