import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Sparkles, Stethoscope, Heart } from 'lucide-react'
import KidPlay from './kid/Play'
import TherapistLogin from './therapist/Login'
import ParentAuth from './parent/ParentAuth'

const ROLES = [
  { key: 'kid',        label: "I'm a Kid!",       icon: Sparkles,    accent: 'ember' },
  { key: 'therapist',  label: 'Therapist/Teacher', icon: Stethoscope, accent: 'mint' },
  { key: 'parent',     label: 'Parent',            icon: Heart,       accent: 'coral' },
]

const ACCENT_CLASSES = {
  ember:  { active: 'bg-ember text-ink', idle: 'text-paper/50 hover:text-paper' },
  mint:   { active: 'bg-mint text-ink', idle: 'text-paper/50 hover:text-paper' },
  coral:  { active: 'bg-coral text-paper', idle: 'text-paper/50 hover:text-paper' },
}

function RoleTabs({ role, setRole }) {
  return (
    <div className="fixed top-0 inset-x-0 z-30 flex justify-center pt-5 px-4 pointer-events-none">
      <div className="pointer-events-auto flex gap-1 p-1 rounded-full bg-black/30 backdrop-blur-xl border border-white/15 shadow-xl shadow-black/30">
        {ROLES.map(({ key, label, icon: Icon, accent }) => {
          const a = ACCENT_CLASSES[accent]
          const active = role === key
          return (
            <button
              key={key}
              type="button"
              onClick={() => setRole(key)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold
                          transition-all whitespace-nowrap ${active ? a.active + ' shadow-sm' : a.idle}`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function AuthPage({ initialRole }) {
  const [searchParams] = useSearchParams()
  const startRole = initialRole || searchParams.get('role') || 'kid'
  const [role, setRole] = useState(ROLES.some(r => r.key === startRole) ? startRole : 'kid')

  return (
    <div className="relative">
      <RoleTabs role={role} setRole={setRole} />
      {role === 'kid' && <KidPlay />}
      {role === 'therapist' && <TherapistLogin />}
      {role === 'parent' && <ParentAuth />}
    </div>
  )
}
