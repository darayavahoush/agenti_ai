"""
routers/auth.py — Kid PIN auth for BreathQuest, plus candidate lookups
against Assessment's patient/therapist records.

Therapist register/login live at app/routers/therapist_auth.py instead
(mounted at the same /api/v1/auth/register and /api/v1/auth/login paths
this router used to define) -- that one is backed by the canonical
`therapists` table; this router's old register/login used the retiring
`breathquest_therapists` table and were removed 2026-08-12 to avoid a
silent route collision if both were ever mounted together, and because
get_current_therapist (gating patients.py/dashboard.py/chime.py) already
only recognizes the canonical table's tokens -- the old endpoints here
issued tokens those routes could never actually accept.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from datetime import datetime, timezone

from app.database import get_db, SessionLocal
from app.models.breathquest_models import (
    BreathQuestPatient, Parent, Subscription,
    TherapistNote, Assignment, Goal, Message, HomePracticeLog,
    GameSession,
)
from app.models.patient import Patient
from app.models.therapist import Therapist
from app.models.vaakmirror_models import VaakMirrorSession, Attempt
from app.models.voicehurdlerace_models import VoiceHurdleRaceSession
from app.models.flashcards_models import PhonemeMastery, FlashcardAttempt
from app.schemas.breathquest_schemas import (
    KidLoginRequest, KidTokenResponse, KidRegisterRequest, KidPinSetupRequest,
    ParentRegisterRequest, ParentLoginRequest, ParentTokenResponse,
    ParentKidRegisterRequest, ParentGoogleLoginRequest, ParentGoogleRegisterRequest,
    ForgotEmailRequest,
    ForgotPlayerCodeRequest,)
from app.breathquest_core.google_oauth import verify_google_id_token
from app.breathquest_core.security import (
    hash_pin, verify_pin, create_kid_token, generate_unique_player_code,
    hash_password, verify_password, create_parent_token, create_access_token,
    create_refresh_token, get_valid_refresh_token, revoke_refresh_token,
)
from app.services.email import send_account_reminder_email, send_player_code_email
from app.breathquest_core.login_throttle import check_throttle, record_failure, record_success
# IP-based limiter (distinct from the per-identifier login_throttle above):
# registration abuse is many different emails from one source, not repeated
# attempts against one account, so this is the right tool here instead.
from app.breathquest_core.rate_limit import check_ip_rate_limit
from app.schemas.breathquest_schemas import RefreshTokenRequest, RefreshTokenResponse
from app.breathquest_core.parental_consent import check_parental_consent
from app.breathquest_core.deps import get_current_parent, get_current_patient, get_current_therapist
from sqlalchemy import delete as sa_delete


async def _delete_patient_cascade(db: AsyncSession, patient_id) -> None:
    """Deletes every row across every table that FKs to this patient,
    explicitly and in dependency order, rather than relying on
    BreathQuestPatient's ORM-level cascade='all, delete-orphan'
    relationships firing correctly in an async session (which requires
    those relationships to already be loaded -- not guaranteed here).
    VaakMirror has no real FK (patient_id is a loose string column), so
    it's deleted via a join on session_id instead of a direct filter.
    Caller is responsible for db.commit()."""
    pid_str = str(patient_id)

    vm_session_ids = (await db.execute(
        select(VaakMirrorSession.id).where(VaakMirrorSession.patient_id == pid_str)
    )).scalars().all()
    if vm_session_ids:
        await db.execute(sa_delete(Attempt).where(Attempt.session_id.in_(vm_session_ids)))
    await db.execute(sa_delete(VaakMirrorSession).where(VaakMirrorSession.patient_id == pid_str))

    await db.execute(sa_delete(VoiceHurdleRaceSession).where(VoiceHurdleRaceSession.patient_id == patient_id))
    await db.execute(sa_delete(PhonemeMastery).where(PhonemeMastery.patient_id == patient_id))
    await db.execute(sa_delete(FlashcardAttempt).where(FlashcardAttempt.patient_id == patient_id))

    await db.execute(sa_delete(GameSession).where(GameSession.patient_id == patient_id))
    await db.execute(sa_delete(TherapistNote).where(TherapistNote.patient_id == patient_id))
    await db.execute(sa_delete(Assignment).where(Assignment.patient_id == patient_id))
    await db.execute(sa_delete(Goal).where(Goal.patient_id == patient_id))
    await db.execute(sa_delete(Message).where(Message.patient_id == patient_id))
    await db.execute(sa_delete(HomePracticeLog).where(HomePracticeLog.patient_id == patient_id))

    parent_row = (await db.execute(select(Parent).where(Parent.patient_id == patient_id))).scalar_one_or_none()
    if parent_row:
        await db.execute(sa_delete(Subscription).where(Subscription.owner_parent_id == parent_row.id))
    await db.execute(sa_delete(Parent).where(Parent.patient_id == patient_id))

    await db.execute(sa_delete(BreathQuestPatient).where(BreathQuestPatient.id == patient_id))

router = APIRouter(prefix="/auth", tags=["auth"])


# ------------------------------------------------------------------ #
#  Therapist candidate lookup (Assessment cross-reference)              #
# ------------------------------------------------------------------ #

@router.get("/therapist-candidates")
def therapist_candidates():
    """Return unique therapist names already recorded during Assessment."""
    sync_db = SessionLocal()
    try:
        names = (
            sync_db.query(Patient.therapist_name)
            .filter(Patient.therapist_name.isnot(None), func.trim(Patient.therapist_name) != "")
            .distinct()
            .order_by(Patient.therapist_name)
            .all()
        )
        return [name for (name,) in names]
    finally:
        sync_db.close()


# ------------------------------------------------------------------ #
#  Kid self-registration                                               #
# ------------------------------------------------------------------ #

@router.get("/kid-candidates")
def kid_candidates():
    """Return children already created through Assessment for PIN setup."""
    sync_db = SessionLocal()
    try:
        patients = sync_db.query(Patient).filter(Patient.is_active.is_(True)).order_by(Patient.name).all()
        return [{"id": str(patient.id), "name": patient.name} for patient in patients]
    finally:
        sync_db.close()

@router.post("/kid-register", response_model=KidTokenResponse, status_code=201)
async def kid_register(request: Request, data: KidRegisterRequest, db: AsyncSession = Depends(get_db)):
    check_ip_rate_limit(request)
    """Brand-new self-serve kid signup — no prior Assessment record
    required. This is what frontend/src/context/AuthContext.jsx's
    registerKid() (used by pages/kid/Play.jsx's signup form) actually
    calls; it only ever sends {first_name, avatar, pin}. The old
    patient_id-required version of this endpoint made every one of those
    calls 422. That link-an-existing-Assessment-patient flow now lives at
    POST /auth/kid-pin-setup instead.

    COPPA: this is the only kid-account path with no adult already in the
    loop, so it's gated on a recently-verified parent email AND phone
    (both required, see breathquest_core/parental_consent.py) before it
    will touch the DB at all."""
    consent = await check_parental_consent(data.parent_email, data.parent_phone, db)
    if not consent.granted:
        detail_by_reason = {
            "email_not_verified": "A parent needs to verify their email before creating this account",
            "email_expired": "Please verify the parent's email again before creating the account",
            "phone_not_verified": "A parent needs to verify their phone number before creating this account",
            "phone_expired": "Please verify the parent's phone number again before creating the account",
        }
        detail = detail_by_reason.get(consent.reason, "A parent needs to verify their email and phone before creating this account")
        raise HTTPException(status_code=403, detail=detail)

    player_code = await generate_unique_player_code(db, data.avatar)
    patient = BreathQuestPatient(
        therapist_id=None,
        first_name=data.first_name,
        avatar=data.avatar,
        pin_hash=hash_pin(data.pin),
        player_code=player_code,
        parent_email=data.parent_email,
        parent_consent_verified_at=consent.email_verified_at,
        parent_phone=data.parent_phone,
        parent_phone_consent_verified_at=consent.phone_verified_at,
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    token = create_kid_token(patient.id)
    refresh_token = await create_refresh_token(db, "patient", str(patient.id))
    await db.commit()
    return KidTokenResponse(
        access_token=token,
        refresh_token=refresh_token,
        patient_id=str(patient.id),
        first_name=patient.first_name,
        avatar=patient.avatar,
        avatar_photo_url=patient.avatar_photo_url,
        player_code=patient.player_code,
        assessment_completed=patient.assessment_completed,
    )


@router.post("/parent-kid-register", response_model=ParentTokenResponse, status_code=201)
async def parent_kid_register(request: Request, data: ParentKidRegisterRequest, db: AsyncSession = Depends(get_db)):
    check_ip_rate_limit(request)
    """Parent-initiated combined signup, no therapist -- creates the kid
    account and links a parent account to it in one transaction. See
    ParentKidRegisterRequest's docstring for how this differs from the
    existing kid-register -> parent-register two-step flow."""
    consent = await check_parental_consent(data.email, data.phone, db)
    if not consent.granted:
        detail_by_reason = {
            "email_not_verified": "Please verify your email before registering",
            "email_expired": "Please verify your email again before registering",
            "phone_not_verified": "Please verify your phone number before registering",
            "phone_expired": "Please verify your phone number again before registering",
        }
        detail = detail_by_reason.get(consent.reason, "Please verify your email and phone before registering")
        raise HTTPException(status_code=403, detail=detail)

    existing_parent_email = await db.execute(select(Parent).where(Parent.email == data.email))
    if existing_parent_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    player_code = await generate_unique_player_code(db, data.avatar)
    patient = BreathQuestPatient(
        therapist_id=None,
        first_name=data.first_name,
        avatar=data.avatar,
        pin_hash=hash_pin(data.pin),
        player_code=player_code,
        parent_email=data.email,
        parent_consent_verified_at=consent.email_verified_at,
        parent_phone=data.phone,
        parent_phone_consent_verified_at=consent.phone_verified_at,
    )
    db.add(patient)
    await db.flush()  # get patient.id without committing yet

    parent = Parent(
        patient_id=patient.id,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
    )
    db.add(parent)
    await db.commit()
    await db.refresh(parent)

    return await _make_parent_token_response(db, parent, patient.first_name)


@router.delete("/parent-account", status_code=204)
async def delete_parent_account(
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    """Deletes the parent's account AND their linked child's account +
    all game data (see _delete_patient_cascade) -- a parent account has
    no meaning without its one linked child in this app's model."""
    await _delete_patient_cascade(db, parent.patient_id)
    await db.commit()


@router.delete("/account", status_code=204)
async def delete_therapist_account(
    therapist: Therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    """Deletes the therapist's own account. Does NOT cascade-delete their
    patients -- a therapist leaving shouldn't destroy a kid's account or
    progress. Nullable FKs (BreathQuestPatient.therapist_id,
    Subscription.owner_therapist_id, Patient.registered_therapist_id) are
    detached instead. TherapistNote.therapist_id is NOT nullable (notes
    are authored content, not a loose reference), so those rows are
    deleted outright rather than left dangling."""
    await db.execute(
        sa_delete(TherapistNote).where(TherapistNote.therapist_id == therapist.id)
    )
    await db.execute(
        BreathQuestPatient.__table__.update()
        .where(BreathQuestPatient.therapist_id == therapist.id)
        .values(therapist_id=None)
    )
    await db.execute(
        Subscription.__table__.update()
        .where(Subscription.owner_therapist_id == therapist.id)
        .values(owner_therapist_id=None)
    )
    await db.execute(sa_delete(Therapist).where(Therapist.id == therapist.id))
    await db.commit()

    # Patient (Assessment's model) lives on a separate sync session, same
    # as kid_pin_setup's main_patient lookup above -- not part of the
    # async `db` session at all.
    sync_db = SessionLocal()
    try:
        sync_db.query(Patient).filter(
            Patient.registered_therapist_id == therapist.id
        ).update({Patient.registered_therapist_id: None})
        sync_db.commit()
    finally:
        sync_db.close()


@router.delete("/kid-account", status_code=204)
async def delete_kid_account(
    patient: BreathQuestPatient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """Kid deletes their own account -- also removes any linked Parent
    row, same cascade as the parent-initiated delete above."""
    await _delete_patient_cascade(db, patient.id)
    await db.commit()


@router.post("/kid-pin-setup", response_model=KidTokenResponse, status_code=201)
async def kid_pin_setup(data: KidPinSetupRequest, db: AsyncSession = Depends(get_db)):
    """Set or reset a BreathQuest PIN for a child already created in
    Assessment (via POST /patients/). This is the endpoint
    AuthContext.jsx's setupKidPin() calls -- it used to point at a route
    that didn't exist at all (404 on every call), since this logic
    previously lived under /auth/kid-register instead."""
    sync_db = SessionLocal()
    try:
        main_patient = sync_db.get(Patient, data.patient_id)
    finally:
        sync_db.close()

    if not main_patient or not main_patient.is_active:
        raise HTTPException(status_code=404, detail="Registered child not found")

    player_code = f"P{str(main_patient.id).replace('-', '')[:9].upper()}"
    result = await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.player_code == player_code))
    patient = result.scalar_one_or_none()

    if patient:
        patient.first_name = main_patient.name
        patient.avatar = data.avatar
        patient.pin_hash = hash_pin(data.pin)
        patient.is_active = True
    else:
        patient = BreathQuestPatient(
            therapist_id=None,
            first_name=main_patient.name,
            avatar=data.avatar,
            pin_hash=hash_pin(data.pin),
            player_code=player_code,
            assessment_patient_id=main_patient.id,
            assessment_completed=True,  # they already have an Assessment record
        )
        db.add(patient)

    await db.commit()
    await db.refresh(patient)
    token = create_kid_token(patient.id)
    return KidTokenResponse(
        access_token=token,
        patient_id=str(patient.id),
        first_name=patient.first_name,
        avatar=patient.avatar,
        player_code=patient.player_code,
        assessment_completed=patient.assessment_completed,
    )

@router.post("/forgot-email", status_code=202)
async def forgot_email(request: Request, data: ForgotEmailRequest, db: AsyncSession = Depends(get_db)):
    """A parent who forgot which email they registered with provides
    their child's player code; if a linked Parent account exists, we
    email that account's own address as a reminder. Always returns
    the same generic response either way -- a response that varied
    by whether the code matched would let this endpoint be used to
    enumerate valid player codes."""
    check_ip_rate_limit(request)
    identifier = data.player_code.strip().upper()
    result = await db.execute(
        select(BreathQuestPatient).where(BreathQuestPatient.player_code == identifier)
    )
    patient = result.scalar_one_or_none()
    if patient:
        parent_result = await db.execute(select(Parent).where(Parent.patient_id == patient.id))
        parent = parent_result.scalar_one_or_none()
        if parent:
            send_account_reminder_email(parent.email, patient.player_code)
    return {"message": "If that player code has a linked parent account, a reminder has been sent to the registered email."}


@router.post("/forgot-player-code", status_code=202)
async def forgot_player_code(request: Request, data: ForgotPlayerCodeRequest, db: AsyncSession = Depends(get_db)):
    """A parent who forgot their child's player code provides their own
    login email; if a linked BreathQuestPatient exists, we email that
    account's player code to the address on file. Always returns the
    same generic response either way -- a response that varied by
    whether the email matched would let this endpoint be used to
    enumerate registered parent emails."""
    check_ip_rate_limit(request)
    email = data.email.strip().lower()
    result = await db.execute(select(Parent).where(Parent.email == email))
    parent = result.scalar_one_or_none()
    if parent:
        patient_result = await db.execute(
            select(BreathQuestPatient).where(BreathQuestPatient.id == parent.patient_id)
        )
        patient = patient_result.scalar_one_or_none()
        if patient:
            send_player_code_email(parent.email, patient.player_code)
    return {"message": "If that email has a linked account, a reminder has been sent with the player code."}


@router.post("/kid-login", response_model=KidTokenResponse)
async def kid_login(data: KidLoginRequest, db: AsyncSession = Depends(get_db)):
    # Player codes remain supported for children who already have one. Names
    # are matched without regard to case so children can use their registered
    # name together with their PIN.
    identifier = data.player_code.strip()

    # Throttle check happens before touching pin_hash at all -- a locked-out
    # identifier gets 429 regardless of whether the PIN they sent is even
    # close, so a locked-out attacker learns nothing from further guesses.
    throttle = await check_throttle(identifier, db)
    if throttle.locked:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please try again later.",
            headers={"Retry-After": str(throttle.retry_after_seconds)},
        )

    result = await db.execute(
        select(BreathQuestPatient).where(
            (BreathQuestPatient.player_code == identifier.upper())
            | (func.lower(BreathQuestPatient.first_name) == identifier.lower())
        )
    )
    patients = result.scalars().all()

    # More than one child can have the same name. The PIN identifies the
    # matching account; their player code remains a fallback for a collision.
    matching_patients = [patient for patient in patients if verify_pin(data.pin, patient.pin_hash)]
    if not matching_patients:
        await record_failure(identifier, db)
        await db.commit()
        raise HTTPException(status_code=401, detail="Incorrect name, player code, or PIN")
    if len(matching_patients) > 1:
        raise HTTPException(status_code=409, detail="More than one player matches. Please use your player code.")

    patient = matching_patients[0]

    if not patient.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token = create_kid_token(patient.id)
    refresh_token = await create_refresh_token(db, "patient", str(patient.id))
    await record_success(identifier, db)
    await db.commit()
    return KidTokenResponse(
        access_token=token,
        refresh_token=refresh_token,
        patient_id=str(patient.id),
        first_name=patient.first_name,
        avatar=patient.avatar,
        avatar_photo_url=patient.avatar_photo_url,
        player_code=patient.player_code,
        assessment_completed=patient.assessment_completed,
    )


# ------------------------------------------------------------------ #
#  Parent auth                                                         #
# ------------------------------------------------------------------ #
# Added 2026-08-13: frontend/src/context/AuthContext.jsx's registerParent()
# and loginParent() (used by pages/parent/ParentAuth.jsx) have called
# authAPI.parentRegister()/parentLogin() -- POST /auth/parent-register and
# POST /auth/parent-login -- since they were written, but no route ever
# served either path; every call 404'd. The Parent model, hash_password/
# verify_password, and create_parent_token/decode_parent_token all already
# existed (see breathquest_core/security.py and breathquest_core/deps.py's
# get_current_parent), so this was purely a missing router, not missing
# infrastructure.
#
# invite_code is accepted by the schema (ParentAuth.jsx already has a UI
# toggle for it) but there's no invite-code generation/storage anywhere in
# the backend yet -- that's a separate, larger feature (a code needs to be
# generated by a therapist, stored, and redeemed exactly once). Rather than
# silently no-op or pretend it works, an invite_code attempt gets a clear
# 501 for now; player_code (fully real -- BreathQuestPatient.player_code)
# is the only working path today.

async def _make_parent_token_response(db: AsyncSession, parent: Parent, child_first_name: str) -> ParentTokenResponse:
    token = create_parent_token(str(parent.id))
    refresh_token = await create_refresh_token(db, "parent", str(parent.id))
    await db.commit()
    return ParentTokenResponse(
        access_token=token,
        refresh_token=refresh_token,
        parent_id=str(parent.id),
        patient_id=str(parent.patient_id),
        email=parent.email,
        phone=parent.phone,
        child_first_name=child_first_name,
    )


@router.post("/parent-register", response_model=ParentTokenResponse, status_code=201)
async def register_parent(request: Request, data: ParentRegisterRequest, db: AsyncSession = Depends(get_db)):
    check_ip_rate_limit(request)
    if not data.player_code and not data.invite_code:
        raise HTTPException(status_code=400, detail="A player code or invite code is required")
    if data.invite_code:
        raise HTTPException(status_code=501, detail="Invite codes aren't available yet — use your child's player code instead")

    result = await db.execute(
        select(BreathQuestPatient).where(BreathQuestPatient.player_code == data.player_code.strip().upper())
    )
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=404, detail="No child found with that player code")

    existing_email = await db.execute(select(Parent).where(Parent.email == data.email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    existing_link = await db.execute(select(Parent).where(Parent.patient_id == child.id))
    if existing_link.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This child already has a linked parent account")

    parent = Parent(
        patient_id=child.id,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
    )
    db.add(parent)
    await db.commit()
    await db.refresh(parent)
    return await _make_parent_token_response(db, parent, child.first_name)


@router.post("/parent-login", response_model=ParentTokenResponse)
async def login_parent(data: ParentLoginRequest, db: AsyncSession = Depends(get_db)):
    throttle = await check_throttle(data.email, db)
    if throttle.locked:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please try again later.",
            headers={"Retry-After": str(throttle.retry_after_seconds)},
        )

    result = await db.execute(select(Parent).where(Parent.email == data.email))
    parent = result.scalar_one_or_none()
    if not parent or not verify_password(data.password, parent.hashed_password):
        await record_failure(data.email, db)
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not parent.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    await record_success(data.email, db)

    child_result = await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.id == parent.patient_id))
    child = child_result.scalar_one_or_none()

    parent.last_login = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return await _make_parent_token_response(db, parent, child.first_name if child else "")


# ------------------------------------------------------------------ #
#  Parent auth via Google                                              #
# ------------------------------------------------------------------ #
# Split into google-login / google-register the same way the password
# flow is split into parent-login / parent-register (see that section's
# comment) -- and for the same reason: Parent.patient_id is required, so
# a Google identity alone is never enough to create an account, only to
# authenticate one that's already linked to a child.

async def _find_parent_by_google(db: AsyncSession, google_user):
    """Looks up an existing Parent by google_sub first, then by email
    (linking it if found and Google-verified) -- same two-step lookup
    therapist_auth.py's /auth/google uses, see that endpoint's docstring
    for why email-linking requires email_verified."""
    result = await db.execute(select(Parent).where(Parent.google_sub == google_user.sub))
    parent = result.scalar_one_or_none()
    if parent is not None or not google_user.email:
        return parent

    result = await db.execute(select(Parent).where(Parent.email == google_user.email))
    existing = result.scalar_one_or_none()
    if existing is None:
        return None
    if not google_user.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Google account email isn't verified -- can't link to an existing account",
        )
    existing.google_sub = google_user.sub
    return existing


@router.post("/parent-google-login", response_model=ParentTokenResponse)
async def login_parent_google(data: ParentGoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    google_user = verify_google_id_token(data.id_token)
    parent = await _find_parent_by_google(db, google_user)
    if parent is None:
        raise HTTPException(
            status_code=404,
            detail="No parent account is linked to this Google email yet -- register with your child's player code first",
        )
    if not parent.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    child_result = await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.id == parent.patient_id))
    child = child_result.scalar_one_or_none()

    parent.last_login = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return await _make_parent_token_response(db, parent, child.first_name if child else "")


@router.post("/parent-google-register", response_model=ParentTokenResponse, status_code=201)
async def register_parent_google(request: Request, data: ParentGoogleRegisterRequest, db: AsyncSession = Depends(get_db)):
    check_ip_rate_limit(request)
    if not data.player_code and not data.invite_code:
        raise HTTPException(status_code=400, detail="A player code or invite code is required")
    if data.invite_code:
        raise HTTPException(status_code=501, detail="Invite codes aren't available yet — use your child's player code instead")

    google_user = verify_google_id_token(data.id_token)
    if not google_user.email_verified:
        raise HTTPException(status_code=403, detail="Google account email isn't verified")

    existing = await _find_parent_by_google(db, google_user)
    if existing is not None:
        raise HTTPException(status_code=400, detail="An account already exists for this Google email — sign in instead")

    result = await db.execute(
        select(BreathQuestPatient).where(BreathQuestPatient.player_code == data.player_code.strip().upper())
    )
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=404, detail="No child found with that player code")

    existing_link = await db.execute(select(Parent).where(Parent.patient_id == child.id))
    if existing_link.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This child already has a linked parent account")

    parent = Parent(
        patient_id=child.id,
        email=google_user.email,
        hashed_password=None,
        full_name=google_user.name,
        phone=data.phone,
        google_sub=google_user.sub,
    )
    db.add(parent)
    await db.commit()
    await db.refresh(parent)
    return await _make_parent_token_response(db, parent, child.first_name)


# ------------------------------------------------------------------ #
#  Refresh / logout (shared across all owner kinds)                    #
# ------------------------------------------------------------------ #
# Single pair of endpoints for therapist/parent/patient alike -- the
# refresh token itself carries owner_kind (see RefreshToken model), so the
# client never needs to specify which account type it's refreshing.
# Refresh rotates the token (old one revoked, new one issued) rather than
# reusing it -- standard practice so a leaked-then-used refresh token is
# only usable once before the legitimate client's next refresh silently
# invalidates it.

_ACCESS_TOKEN_FACTORIES = {
    "therapist": lambda owner_id: create_access_token(owner_id),
    "parent": lambda owner_id: create_parent_token(owner_id),
    "patient": lambda owner_id: create_kid_token(owner_id),
}


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_access_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    token = await get_valid_refresh_token(db, data.refresh_token)
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    factory = _ACCESS_TOKEN_FACTORIES.get(token.owner_kind)
    if factory is None:
        raise HTTPException(status_code=500, detail="Unknown token owner kind")

    token.revoked_at = datetime.now(timezone.utc)
    new_refresh_token = await create_refresh_token(db, token.owner_kind, str(token.owner_id))
    new_access_token = factory(str(token.owner_id))
    await db.commit()

    return RefreshTokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post("/logout", status_code=204)
async def logout(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    await revoke_refresh_token(db, data.refresh_token)
    await db.commit()
