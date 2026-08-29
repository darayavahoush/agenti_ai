import { createContext, useContext, useState, useEffect } from 'react'
import { authAPI, assessmentAPI, patientsAPI } from '../api/client'

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

  useEffect(() => {
    const token    = localStorage.getItem('bq_token')
    const userType = localStorage.getItem('bq_user_type')
    const userData = localStorage.getItem('bq_user_data')
    if (token && userData) {
      const parsed = JSON.parse(userData)
      if (userType === 'therapist') setTherapist(parsed)
      if (userType === 'patient')   setPatient(parsed)
      if (userType === 'parent')    setParent(parsed)
    }
    const backupRaw = localStorage.getItem('bq_supervisor_backup')
    if (backupRaw) {
      try { setSupervisorBackup(JSON.parse(backupRaw)) } catch { /* corrupt -- ignore */ }
    }
    setLoading(false)
  }, [])

  const loginTherapist = async (email, password) => {
    const { data } = await authAPI.login({ email, password })
    localStorage.setItem('bq_token',         data.access_token)
    localStorage.setItem('bq_refresh_token', data.refresh_token)
    localStorage.setItem('bq_user_type',     'therapist')
    localStorage.setItem('bq_user_data',     JSON.stringify(data))
    setTherapist(data); setPatient(null); setParent(null)
    return data
  }

  // Combined login-or-register, matching the backend's single POST
  // /auth/google endpoint -- unlike password auth there's no separate
  // registerTherapistGoogle, since a therapist account needs nothing
  // beyond what the verified Google token already gives us.
  const loginTherapistGoogle = async (idToken) => {
    const { data } = await authAPI.googleAuthTherapist(idToken)
    localStorage.setItem('bq_token',         data.access_token)
    localStorage.setItem('bq_refresh_token', data.refresh_token)
    localStorage.setItem('bq_user_type',     'therapist')
    localStorage.setItem('bq_user_data',     JSON.stringify(data))
    setTherapist(data); setPatient(null); setParent(null)
    return data
  }

  const registerTherapist = async (formData) => {
    const { data } = await authAPI.register(formData)
    localStorage.setItem('bq_token',         data.access_token)
    localStorage.setItem('bq_refresh_token', data.refresh_token)
    localStorage.setItem('bq_user_type',     'therapist')
    localStorage.setItem('bq_user_data',     JSON.stringify(data))
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
    localStorage.setItem('bq_token',         data.access_token)
    localStorage.setItem('bq_refresh_token', data.refresh_token)
    localStorage.setItem('bq_user_type',     'patient')
    localStorage.setItem('bq_user_data',     JSON.stringify(data))
    setPatient(data); setTherapist(null); setParent(null)
    return data
  }

  const setupKidPin = async (assessmentPatientId, avatar, pin) => {
    const { data } = await authAPI.kidPinSetup({ patient_id: assessmentPatientId, avatar, pin })
    localStorage.setItem('bq_token',         data.access_token)
    localStorage.setItem('bq_refresh_token', data.refresh_token)
    localStorage.setItem('bq_user_type',     'patient')
    localStorage.setItem('bq_user_data',     JSON.stringify(data))
    setPatient(data); setTherapist(null); setParent(null)
    return data
  }

  const loginKid = async (playerCode, pin) => {
    const { data } = await authAPI.kidLogin({ player_code: playerCode, pin })
    localStorage.setItem('bq_token',         data.access_token)
    localStorage.setItem('bq_refresh_token', data.refresh_token)
    localStorage.setItem('bq_user_type',     'patient')
    localStorage.setItem('bq_user_data',     JSON.stringify(data))
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
      localStorage.setItem('bq_token',         data.access_token)
      localStorage.setItem('bq_refresh_token', data.refresh_token)
      localStorage.setItem('bq_user_type',     'parent')
      localStorage.setItem('bq_user_data',     JSON.stringify(data))
      setParent(data); setTherapist(null); setPatient(null)
      return data
    }
    const payload = {
      email, password, full_name: fullName, phone,
      [codeType === 'invite' ? 'invite_code' : 'player_code']: code,
    }
    const { data } = await authAPI.parentRegister(payload)
    localStorage.setItem('bq_token',         data.access_token)
    localStorage.setItem('bq_refresh_token', data.refresh_token)
    localStorage.setItem('bq_user_type',     'parent')
    localStorage.setItem('bq_user_data',     JSON.stringify(data))
    setParent(data); setTherapist(null); setPatient(null)
    return data
  }

  // Shared by all three delete-account flows: clears every piece of
  // local auth state regardless of which role called it, since deleting
  // an account should always end in a fully logged-out state (same
  // cleanup logout() already does).
  const _clearSession = () => {
    localStorage.removeItem('bq_token')
    localStorage.removeItem('bq_refresh_token')
    localStorage.removeItem('bq_user_type')
    localStorage.removeItem('bq_user_data')
    setParent(null); setTherapist(null); setPatient(null)
  }

  const deleteParentAccount = async () => {
    await authAPI.deleteParentAccount()
    _clearSession()
  }

  const deleteKidAccount = async () => {
    await authAPI.deleteKidAccount()
    _clearSession()
  }

  const deleteTherapistAccount = async () => {
    await authAPI.deleteTherapistAccount()
    _clearSession()
  }

  const loginParent = async (email, password) => {
    const { data } = await authAPI.parentLogin({ email, password })
    localStorage.setItem('bq_token',         data.access_token)
    localStorage.setItem('bq_refresh_token', data.refresh_token)
    localStorage.setItem('bq_user_type',     'parent')
    localStorage.setItem('bq_user_data',     JSON.stringify(data))
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
    localStorage.setItem('bq_token',         data.access_token)
    localStorage.setItem('bq_refresh_token', data.refresh_token)
    localStorage.setItem('bq_user_type',     'parent')
    localStorage.setItem('bq_user_data',     JSON.stringify(data))
    setParent(data); setTherapist(null); setPatient(null)
    return data
  }

  const registerParentGoogle = async ({ idToken, code, codeType, phone }) => {
    const payload = {
      id_token: idToken, phone,
      [codeType === 'invite' ? 'invite_code' : 'player_code']: code,
    }
    const { data } = await authAPI.parentGoogleRegister(payload)
    localStorage.setItem('bq_token',         data.access_token)
    localStorage.setItem('bq_refresh_token', data.refresh_token)
    localStorage.setItem('bq_user_type',     'parent')
    localStorage.setItem('bq_user_data',     JSON.stringify(data))
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
    localStorage.removeItem('bq_token')
    localStorage.removeItem('bq_refresh_token')
    localStorage.removeItem('bq_user_type')
    localStorage.removeItem('bq_user_data')
    localStorage.removeItem('bq_supervisor_backup')
    setSupervisorBackup(null)
    setTherapist(null); setPatient(null); setParent(null)
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
