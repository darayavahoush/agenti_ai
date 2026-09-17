import { useAuth } from '../../context/AuthContext'
import { TrendingUp, Settings } from 'lucide-react'
import AboutPage from '../shared/AboutPage'

export default function ParentAboutPage() {
  const { parent, logout } = useAuth()
  return (
    <AboutPage
      role="parent"
      sidebarItems={[
        { label: 'Progress', icon: TrendingUp, to: '/parent/dashboard' },
        { label: 'Settings', icon: Settings, to: '/parent/settings' },
      ]}
      name={parent?.child_first_name ? `${parent.child_first_name}'s Progress` : undefined}
      onLogout={logout}
      homeTo="/parent/dashboard"
      homeLabel="Back to progress"
    />
  )
}
