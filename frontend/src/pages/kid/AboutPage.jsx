import { useAuth } from '../../context/AuthContext'
import { KID_SIDEBAR_ITEMS } from '../../lib/kidSidebarItems'
import AboutPage from '../shared/AboutPage'

export default function KidAboutPage() {
  const { patient, logout } = useAuth()
  return (
    <AboutPage
      role="kid"
      sidebarItems={KID_SIDEBAR_ITEMS}
      name={patient?.first_name}
      onLogout={logout}
      homeTo="/play"
      homeLabel="Back to games"
    />
  )
}
