import { useAuth } from '../../context/AuthContext'
import { LayoutDashboard, Settings } from 'lucide-react'
import AboutPage from '../shared/AboutPage'

export default function TherapistAboutPage() {
  const { therapist, logout } = useAuth()
  return (
    <AboutPage
      role="therapist"
      sidebarItems={[
        { label: 'Dashboard', icon: LayoutDashboard, to: '/therapist/dashboard' },
        { label: 'Settings', icon: Settings, to: '/therapist/settings' },
      ]}
      name={therapist?.full_name}
      subtitle={therapist?.clinic_name}
      onLogout={logout}
      homeTo="/therapist/dashboard"
      homeLabel="Back to dashboard"
    />
  )
}
