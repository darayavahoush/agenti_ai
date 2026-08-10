import { Navigate } from 'react-router-dom'
import { getAuth } from '../lib/auth.js'

// kind: 'therapist' | 'patient' | undefined (undefined = any authenticated identity)
export default function RequireAuth({ kind, children }) {
  const auth = getAuth()
  if (!auth || (kind && auth.kind !== kind)) {
    return <Navigate to="/vaakmirror/login" replace />
  }
  return children
}
