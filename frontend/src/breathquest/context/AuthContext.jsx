import { createContext, useContext, useState, useEffect } from 'react'
import { authAPI } from '../api/client'

const AuthContext = createContext(null)

function parseJwt(token) {
  try {
    const payload = token.split('.')[1]
    if (!payload) return null
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decodeURIComponent(escape(json)))
  } catch {
    return null
  }
}

function isJwtValid(token) {
  const payload = parseJwt(token)
  if (!payload || !payload.exp) return false
  return Date.now() / 1000 < payload.exp
}

export function AuthProvider({ children }) {
  const [therapist, setTherapist] = useState(null)
  const [patient,   setPatient]   = useState(null)
  const [loading,   setLoading]   = useState(true)

  useEffect(() => {
    const token    = localStorage.getItem('bq_token')
    const userType = localStorage.getItem('bq_user_type')
    const userData = localStorage.getItem('bq_user_data')

    if (token && userData && isJwtValid(token)) {
      const parsed = JSON.parse(userData)
      if (userType === 'therapist') setTherapist(parsed)
      if (userType === 'patient')   setPatient(parsed)
    } else {
      localStorage.removeItem('bq_token')
      localStorage.removeItem('bq_user_type')
      localStorage.removeItem('bq_user_data')
    }

    setLoading(false)
  }, [])

  const loginTherapist = async (email, password) => {
    const { data } = await authAPI.login({ email, password })
    localStorage.setItem('bq_token',     data.access_token)
    localStorage.setItem('bq_user_type', 'therapist')
    localStorage.setItem('bq_user_data', JSON.stringify(data))
    setTherapist(data); setPatient(null)
    return data
  }

  const registerTherapist = async (formData) => {
    const { data } = await authAPI.register(formData)
    localStorage.setItem('bq_token',     data.access_token)
    localStorage.setItem('bq_user_type', 'therapist')
    localStorage.setItem('bq_user_data', JSON.stringify(data))
    setTherapist(data); setPatient(null)
    return data
  }

  const registerKid = async (firstName, avatar, pin) => {
    const { data } = await authAPI.kidRegister({ first_name: firstName, avatar, pin })
    localStorage.setItem('bq_token',     data.access_token)
    localStorage.setItem('bq_user_type', 'patient')
    localStorage.setItem('bq_user_data', JSON.stringify(data))
    setPatient(data); setTherapist(null)
    return data
  }

  const loginKid = async (playerCode, pin) => {
    const { data } = await authAPI.kidLogin({ player_code: playerCode, pin })
    localStorage.setItem('bq_token',     data.access_token)
    localStorage.setItem('bq_user_type', 'patient')
    localStorage.setItem('bq_user_data', JSON.stringify(data))
    setPatient(data); setTherapist(null)
    return data
  }

  const logout = () => {
    localStorage.removeItem('bq_token')
    localStorage.removeItem('bq_user_type')
    localStorage.removeItem('bq_user_data')
    setTherapist(null); setPatient(null)
  }

  return (
    <AuthContext.Provider value={{
      therapist, patient, loading,
      loginTherapist, registerTherapist, loginKid, registerKid, logout,
      isTherapist: !!therapist,
      isKid:       !!patient,
      isLoggedIn:  !!(therapist || patient),
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
