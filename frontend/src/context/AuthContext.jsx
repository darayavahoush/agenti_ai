import { createContext, useContext, useState, useEffect } from 'react'
import { authAPI, assessmentAPI, patientsAPI } from '../api/client'
import { listKnownAccounts, upsertKnownAccount, forgetKnownAccount, currentAccountKey, accountKey } from '../api/knownAccounts'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [therapist, setTherapist] = useState(null)
  const [patient,   setPatient]   = useState(null)
  const [parent,    setParent]    = useState(null)
  const [loading,   setLoading]   = useState(true)
  // Set only while a therapist is supervising a session launched via
  // startSupervisedSession below -- holds the therapist's own session so
  // endSupervisedSession can restore it without a fresh login.
  const [supervisorBackup, setSupervisorBackup] = useState(null)
  // Everyone who has ever logged in on this device, for the profile
  // switcher -- separate from which ONE of them is active right now (that's
  // still just the plain bq_token/bq_user_type/bq_user_data keys below).
  const [knownAccounts, setKnownAccounts] = useState([])
  // A parent's full switchable child list (2026-09-10) -- separate from
  // BOTH the device-level profile switcher above (which swaps which
  // ACCOUNT is active on this device) and `patient` above (which stays
  // the CURRENTLY ACTIVE child within a single parent account, since
  // every existing dashboard/messages/session query already reads it
  // that way). This is purely the set shown in the child-switcher UI.
  const [childrenList, setChildrenList] = useState([])

  // Single place every login/register function below persists a session --
  // sets the four active-session keys, and upserts this account into the
  // device's switcher roster so it's there to switch back into later
  // without re-entering a PIN or password. Also syncs childrenList: only
  // parent sessions carry a `children` list at all, so any other role
  // clears it (a therapist/kid session has no meaning for "which child is
  // active" the way a parent one does).
  const _persistSession = (userType, data) => {
    localStorage.setItem('bq_token',         data.access_token)
    localStorage.setItem('bq_refresh_token', data.refresh_token)
    localStorage.setItem('bq_user_type',     userType)
    localStorage.setItem('bq_user_data',     JSON.stringify(data))
    setKnownAccounts(upsertKnownAccount(userType, data, data.refresh_token))
    if (userType === 'parent') {
      setChildrenList(data.children || [])
      localStorage.setItem('bq_parent_children', JSON.stringify(data.children || []))
    } else {
      setChildrenList([])
      localStorage.removeItem('bq_parent_children')
    }
  }

  useEffect(() => {
    const token    = localStorage.getItem('bq_token')
    const userType = localStorage.getItem('bq_user_type')
    const userData = localStorage.getItem('bq_user_data')
    if (token && userData) {
      try {
        const parsed = JSON.parse(userData)
        if (userType === 'therapist') setTherapist(parsed)
        if (userType === 'patient')   setPatient(parsed)
        if (userType === 'parent')    setParent(parsed)
      } catch {
        // Corrupted bq_user_data (partial write, storage quirk) -- drop the
        // dead session keys rather than leaving them around to fail the
        // same way on every future load, and fall through to a clean
        // logged-out state instead of leaving `loading` stuck true forever
        // (which is what happened before this try/catch existed: an
        // uncaught throw here meant setLoading(false) below never ran).
        localStorage.removeItem('bq_token')
        localStorage.removeItem('bq_refresh_token')
        localStorage.removeItem('bq_user_type')
        localStorage.removeItem('bq_user_data')
      }
    }
    const backupRaw = localStorage.getItem('bq_supervisor_backup')
    if (backupRaw) {
      try { setSupervisorBackup(JSON.parse(backupRaw)) } catch { /* corrupt -- ignore */ }
    }
    if (userType === 'parent') {
      const storedChildren = localStorage.getItem('bq_parent_children')
      if (storedChildren) {
        try { setChildrenList(JSON.parse(storedChildren)) } catch { /* corrupt -- ignore */ }
      }
    }
    setKnownAccounts(listKnownAccounts())
    setLoading(false)
  }, [])

  const loginTherapist = async (email, password) => {
    const { data } = await authAPI.login({ email, password })
    _persistSession('therapist', data)
    setTherapist(data); setPatient(null); setParent(null)
    return data
  }

  // Combined login-or-register, matching the backend's single POST
  // /auth/google endpoint -- unlike password auth there's no separate
  // registerTherapistGoogle, since a therapist account needs nothing
  // beyond what the verified Google token already gives us.
  const loginTherapistGoogle = async (idToken) => {
    const { data } = await authAPI.googleAuthTherapist(idToken)
    _persistSession('therapist', data)
    setTherapist(data); setPatient(null); setParent(null)
    return data
  }

  const registerTherapist = async (formData) => {
    const { data } = await authAPI.register(formData)
    _persistSession('therapist', data)
    setTherapist(data); setPatient(null); setParent(null)
    return data
  }

  // parentPhone is optional -- collected but not verified (phone consent
  // was removed 2026-08-29, see backend parental_consent.py). Kept as a
  // trailing param rather than dropped in case a caller ever wants to
  // pass it through.
  const registerKid = async (firstName, avatar, pin, parentEmail, parentPhone) => {
    const { data } = await authAPI.kidRegister({
      first_name: firstName, avatar, pin,
      parent_email: parentEmail, parent_phone: parentPhone,
    })
    _persistSession('patient', data)
    setPatient(data); setTherapist(null); setParent(null)
    return data
  }

  const setupKidPin = async (assessmentPatientId, avatar, pin) => {
    const { data } = await authAPI.kidPinSetup({ patient_id: assessmentPatientId, avatar, pin })
    _persistSession('patient', data)
    setPatient(data); setTherapist(null); setParent(null)
    return data
  }

  const loginKid = async (playerCode, pin) => {
    const { data } = await authAPI.kidLogin({ player_code: playerCode, pin })
    _persistSession('patient', data)
    setPatient(data); setTherapist(null); setParent(null)
    return data
  }

  // Called once AssessmentGate.jsx's POST /assessment/complete succeeds --
  // updates the in-memory + persisted patient record so ProtectedKid-style
  // redirect checks (and anything reading isKid's assessment_completed
  // flag) see the change immediately, without a fresh login round-trip.
  const markAssessmentComplete = async (summary) => {
    await assessmentAPI.complete({
      words_attempted: summary?.wordsAttempted ?? 0,
      severity_classification: summary?.severityClassification ?? null,
    })
    setPatient((prev) => {
      if (!prev) return prev
      const updated = { ...prev, assessment_completed: true }
      localStorage.setItem('bq_user_data', JSON.stringify(updated))
      return updated
    })
  }

  // Therapist-launched entry point into Assessment/Live Therapy
  // (2026-08-13) -- the structural gap identified alongside the patient-
  // linking fix: previously a kid had to self-login with their own PIN
  // before either flow was reachable, so a therapist creating a patient
  // and wanting to run their first assessment had no way in at all.
  //
  // Stashes the therapist's OWN session (token/type/data) under a
  // separate key before overwriting bq_token/bq_user_type/bq_user_data
  // with the patient's -- so endSupervisedSession can restore it exactly,
  // without a fresh login round-trip. Deliberately a separate localStorage
  // key rather than reusing bq_token itself, since the whole point is to
  // recover the therapist's session after the patient's overwrites it.
  const startSupervisedSession = async (breathQuestPatientId) => {
    const backup = {
      token:        localStorage.getItem('bq_token'),
      refreshToken: localStorage.getItem('bq_refresh_token'),
      userType:     localStorage.getItem('bq_user_type'),
      userData:     localStorage.getItem('bq_user_data'),
    }
    const { data } = await patientsAPI.startSession(breathQuestPatientId)

    localStorage.setItem('bq_supervisor_backup', JSON.stringify(backup))
    setSupervisorBackup(backup)

    localStorage.setItem('bq_token',         data.access_token)
    localStorage.setItem('bq_refresh_token', data.refresh_token)
    localStorage.setItem('bq_user_type',     'patient')
    localStorage.setItem('bq_user_data',     JSON.stringify(data))
    setPatient(data); setTherapist(null); setParent(null)
    return data
  }

  // Restores the therapist's session stashed above. Silently no-ops if
  // there's nothing to restore (e.g. called twice) rather than throwing --
  // this runs from a banner's "Exit session" button, where a confusing
  // error is worse than a harmless no-op.
  const endSupervisedSession = () => {
    if (!supervisorBackup) return
    const { token, refreshToken, userType, userData } = supervisorBackup
    if (token)        localStorage.setItem('bq_token', token)
    if (refreshToken) localStorage.setItem('bq_refresh_token', refreshToken)
    else              localStorage.removeItem('bq_refresh_token')
    if (userType) localStorage.setItem('bq_user_type', userType)
    if (userData) localStorage.setItem('bq_user_data', userData)
    localStorage.removeItem('bq_supervisor_backup')
    setSupervisorBackup(null)

    const parsed = userData ? JSON.parse(userData) : null
    setTherapist(userType === 'therapist' ? parsed : null)
    setPatient(userType === 'patient' ? parsed : null)
    setParent(userType === 'parent' ? parsed : null)
  }


  // codeType distinguishes which field the code goes in ('player_code' vs
  // 'invite_code') — the two ways described in the parent-facing UI:
  // "log in with your kid's existing code" vs "use the code your
  // therapist gave you". A third value, 'new_child', means there's no
  // code at all yet -- the parent is creating both their own account and
  // their child's in one step (POST /auth/parent-kid-register instead of
  // /auth/parent-register), so kidFirstName/kidAvatar/kidPin are used
  // instead of code, and phone is required (dual-factor consent) rather
  // than optional.
  const registerParent = async ({ code, codeType, email, password, fullName, phone, kidFirstName, kidAvatar, kidPin }) => {
    if (codeType === 'new_child') {
      const payload = {
        first_name: kidFirstName, avatar: kidAvatar, pin: kidPin,
        email, password, full_name: fullName, phone,
      }
      const { data } = await authAPI.parentKidRegister(payload)
      _persistSession('parent', data)
      setParent(data); setTherapist(null); setPatient(null)
      return data
    }
    // Invite-code registration isn't implemented on the backend yet
    // (register_parent 501s on invite_code) -- only player_code is real,
    // so this always sends that field rather than branching on a
    // frontend-only distinction the backend can't act on.
    const payload = {
      email, password, full_name: fullName, phone,
      player_code: code,
    }
    const { data } = await authAPI.parentRegister(payload)
    _persistSession('parent', data)
    setParent(data); setTherapist(null); setPatient(null)
    return data
  }

  // Switches which child is active for this parent -- see backend's
  // POST /auth/parent/switch-child docstring for why this doesn't mint
  // new tokens at all (parent identity itself never changes, only which
  // child.patient_id the account currently points at). Updates
  // patient_id/child_first_name in-place on the existing parent object
  // (React state, bq_user_data, AND the device-switcher's own roster
  // entry -- see upsertKnownAccount call below), so every screen reading
  // useAuth().parent.patient_id picks up the new active child immediately,
  // with no re-login.
  //
  // Also re-upserts the known-accounts roster entry, not just bq_user_data
  // -- without this, quick-switching away via the device-level "Switch
  // profile" picker and back into this same parent would silently revert
  // to whichever child was active before this switch (switchAccount reuses
  // the roster's cached userData rather than refetching). Safe to reuse
  // the current refresh token unchanged here since nothing about the
  // token itself changed.
  const switchChild = async (patientId) => {
    const { data } = await authAPI.switchChild(patientId)
    setParent((prev) => {
      if (!prev) return prev
      const next = { ...prev, patient_id: data.patient_id, child_first_name: data.child_first_name }
      localStorage.setItem('bq_user_data', JSON.stringify(next))
      const refreshToken = localStorage.getItem('bq_refresh_token')
      setKnownAccounts(upsertKnownAccount('parent', next, refreshToken))
      return next
    })
    setChildrenList((prev) => {
      const next = prev.map((c) => ({ ...c, is_active: c.patient_id === data.patient_id }))
      localStorage.setItem('bq_parent_children', JSON.stringify(next))
      return next
    })
    return data
  }

  // Creates a brand-new child under the logged-in parent ("add another
  // child") and appends it to the switcher list -- does NOT switch to it
  // automatically; the switcher UI decides whether to call switchChild
  // right after, so a parent adding a child while actively viewing
  // another child's dashboard doesn't get yanked away from what they were
  // looking at.
  const addChild = async (fields) => {
    const { data: child } = await authAPI.addChild({
      first_name: fields.firstName, avatar: fields.avatar, pin: fields.pin,
    })
    setChildrenList((prev) => {
      const next = [...prev, child]
      localStorage.setItem('bq_parent_children', JSON.stringify(next))
      return next
    })
    return child
  }

  // Links an EXISTING child (created elsewhere) to this parent's
  // switcher by player code -- see backend LinkChildRequest's docstring.
  const linkChild = async (playerCode) => {
    const { data: child } = await authAPI.linkChild({ player_code: playerCode })
    setChildrenList((prev) => {
      const next = [...prev, child]
      localStorage.setItem('bq_parent_children', JSON.stringify(next))
      return next
    })
    return child
  }

  // Re-fetches the children list from the backend -- useful after
  // something outside this tab could have changed it (another
  // device/tab adding a child), or just to recover from a stale local
  // cache without a full re-login.
  const refreshChildren = async () => {
    const { data } = await authAPI.getChildren()
    setChildrenList(data.children || [])
    localStorage.setItem('bq_parent_children', JSON.stringify(data.children || []))
    return data.children
  }

  // Shared by all three delete-account flows: clears every piece of
  // local auth state regardless of which role called it, since deleting
  // an account should always end in a fully logged-out state (same
  // cleanup logout() already does).
  // Instantly switches the active session to a different profile already
  // remembered on this device -- no PIN or password re-entry, matching a
  // Netflix-style profile picker. Gets a fresh access/refresh token pair
  // via a real refresh call rather than reusing whatever's cached (the
  // stored refresh token could be idle for days between switches, and
  // refresh both validates it's still alive AND rotates it), but keeps the
  // account's cached display info (name/avatar/etc.) from its last real
  // login rather than re-fetching, since /auth/refresh only ever returns
  // tokens, not profile data.
  const switchAccount = async (key) => {
    const entry = listKnownAccounts().find((a) => a.key === key)
    if (!entry) return { ok: false, reason: 'not_found' }
    try {
      const { data } = await authAPI.refresh(entry.refreshToken)
      const merged = { ...entry.userData, access_token: data.access_token, refresh_token: data.refresh_token }
      _persistSession(entry.userType, merged)
      setTherapist(entry.userType === 'therapist' ? merged : null)
      setPatient(entry.userType === 'patient' ? merged : null)
      setParent(entry.userType === 'parent' ? merged : null)
      setSupervisorBackup(null) // switching profiles ends any supervised-session overlay
      localStorage.removeItem('bq_supervisor_backup')
      return { ok: true, userType: entry.userType }
    } catch {
      // Refresh token itself is dead -- idle past its 14-30 day window, or
      // revoked (e.g. that profile was deleted elsewhere). Can't be
      // quick-switched into anymore; drop it rather than leaving a
      // switcher entry that will just fail the same way next time.
      forgetKnownAccount(key)
      setKnownAccounts(listKnownAccounts())
      return { ok: false, reason: 'expired', userType: entry.userType }
    }
  }

  // Removes one profile from this device's switcher roster. If it's the
  // one currently active, this also ends that session properly (server
  // -side revoke + clearing the active keys) rather than just vanishing it
  // from the list while leaving the user signed in with no way to find it
  // again in the switcher.
  const forgetAccount = async (key) => {
    const wasActive = key === currentAccountKey()
    forgetKnownAccount(key)
    setKnownAccounts(listKnownAccounts())
    if (wasActive) await logout()
  }

  const _clearSession = () => {
    const key = currentAccountKey()
    if (key) forgetKnownAccount(key)
    setKnownAccounts(listKnownAccounts())
    localStorage.removeItem('bq_token')
    localStorage.removeItem('bq_refresh_token')
    localStorage.removeItem('bq_user_type')
    localStorage.removeItem('bq_user_data')
    localStorage.removeItem('bq_parent_children')
    setParent(null); setTherapist(null); setPatient(null)
    setChildrenList([])
  }

  const deleteParentAccount = async (currentPassword) => {
    await authAPI.deleteParentAccount({ current_password: currentPassword })
    _clearSession()
  }

  const deleteKidAccount = async (currentPin) => {
    await authAPI.deleteKidAccount({ current_pin: currentPin })
    _clearSession()
  }

  const deleteTherapistAccount = async (currentPassword) => {
    await authAPI.deleteTherapistAccount({ current_password: currentPassword })
    _clearSession()
  }

  const loginParent = async (email, password) => {
    const { data } = await authAPI.parentLogin({ email, password })
    _persistSession('parent', data)
    setParent(data); setTherapist(null); setPatient(null)
    return data
  }

  // Split into login/register like loginParent/registerParent above --
  // a Google identity alone can't create a Parent account (it still
  // needs a child to link via player_code), so unlike therapist-google
  // this can't be one combined call. registerParentGoogle only covers
  // the "I have a code" path, not "new child, no therapist" -- that
  // combined flow needs phone OTP consent that doesn't have a
  // Google-auth equivalent yet (see backend schema's docstring).
  const loginParentGoogle = async (idToken) => {
    const { data } = await authAPI.parentGoogleLogin(idToken)
    _persistSession('parent', data)
    setParent(data); setTherapist(null); setPatient(null)
    return data
  }

  const registerParentGoogle = async ({ idToken, code, phone }) => {
    // Same simplification as registerParent above -- invite codes aren't
    // a real backend feature yet, only player_code is.
    const payload = {
      id_token: idToken, phone,
      player_code: code,
    }
    const { data } = await authAPI.parentGoogleRegister(payload)
    _persistSession('parent', data)
    setParent(data); setTherapist(null); setPatient(null)
    return data
  }

  // Merges partial patient updates (e.g. from MyAccount.jsx's profile
  // edit) into both React state and the localStorage blob AuthContext
  // itself reads on mount, so a refresh doesn't lose the new name/avatar.
  const updatePatient = (fields) => {
    setPatient((prev) => {
      const next = { ...prev, ...fields }
      try {
        const stored = JSON.parse(localStorage.getItem('bq_user_data') || '{}')
        localStorage.setItem('bq_user_data', JSON.stringify({ ...stored, ...fields }))
      } catch {
        // ignore malformed existing storage
      }
      return next
    })
  }

  const logout = async () => {
    const refreshToken = localStorage.getItem('bq_refresh_token')
    if (refreshToken) {
      // Best-effort server-side revoke -- logout must still succeed locally
      // even if this call fails (network down, refresh token already
      // expired/rotated elsewhere, etc.), so failures are swallowed rather
      // than surfaced to the caller.
      try { await authAPI.logout(refreshToken) } catch { /* ignore */ }
    }
    // An explicit "Log out" is a deliberate "I'm done here" from whoever's
    // using the device -- unlike switchAccount (which leaves the profile
    // you're leaving in the roster to switch back into later), this drops
    // it from the switcher too, matching what a person expects "log out"
    // to mean rather than leaving a ghost entry that still quick-switches
    // back in with no password.
    const key = currentAccountKey()
    if (key) forgetKnownAccount(key)
    setKnownAccounts(listKnownAccounts())
    localStorage.removeItem('bq_token')
    localStorage.removeItem('bq_refresh_token')
    localStorage.removeItem('bq_user_type')
    localStorage.removeItem('bq_user_data')
    localStorage.removeItem('bq_supervisor_backup')
    localStorage.removeItem('bq_parent_children')
    setSupervisorBackup(null)
    setTherapist(null); setPatient(null); setParent(null)
    setChildrenList([])
  }

  return (
    <AuthContext.Provider value={{
      therapist, patient, parent, loading,
      loginTherapist, registerTherapist, loginTherapistGoogle,
      loginKid, registerKid, setupKidPin,
      markAssessmentComplete,
      startSupervisedSession, endSupervisedSession,
      loginParent, registerParent, loginParentGoogle, registerParentGoogle, logout,
      deleteParentAccount, deleteKidAccount, deleteTherapistAccount,
      updatePatient,
      knownAccounts, switchAccount, forgetAccount,
      childrenList, switchChild, addChild, linkChild, refreshChildren,
      currentAccountKey: currentAccountKey(),
      isTherapist: !!therapist,
      isKid:       !!patient,
      isParent:    !!parent,
      isLoggedIn:  !!(therapist || patient || parent),
      isSupervised:    !!supervisorBackup,
      supervisorName:  supervisorBackup?.userData ? JSON.parse(supervisorBackup.userData).full_name : null,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
