import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Sidebar, AmbientGlow, ABOUT_CONTENT } from '../../components/ui'

// Full "About / How to use" page, replacing the old modal -- same
// role-specific copy (see AboutModal.jsx, which still owns ABOUT_CONTENT),
// now laid out as titled sections with icons instead of a wall of
// paragraphs in a small popup. One shared body; each role's thin wrapper
// page (kid/parent/therapist) supplies its own Sidebar wiring (real nav
// items, name, logout) since those differ per role and already live in
// each app's own pages.
export default function AboutPage({ role, sidebarItems, name, subtitle, onLogout, homeTo, homeLabel = 'Back' }) {
  const content = ABOUT_CONTENT[role] || ABOUT_CONTENT.parent

  // Clears the sidebar's unread dot for next time -- previously this flag
  // was set the moment the modal auto-opened; now it's set on an actual
  // visit to the page, which is the more honest signal of "seen it."
  useEffect(() => {
    localStorage.setItem(`bq_seen_about_${role}`, '1')
  }, [role])

  return (
    <div className="min-h-dvh relative flex"
         style={{ background: 'linear-gradient(180deg, #12142E 0%, #241F49 38%, #6B4A8A 78%, #9A5F72 100%)' }}>
      <AmbientGlow />

      <Sidebar role={role} items={sidebarItems} name={name} subtitle={subtitle} onLogout={onLogout} />

      <div className="relative flex-1 min-w-0 max-w-2xl mx-auto px-6 py-10">
        <Link to={homeTo} className="inline-flex items-center gap-1.5 text-white/40 hover:text-white text-sm mb-8 transition-colors">
          <ArrowLeft size={14} />
          {homeLabel}
        </Link>

        <h1 className={`font-display text-2xl font-bold mb-8 ${content.accent}`}>{content.title}</h1>

        <div className="flex flex-col gap-4">
          {content.sections.map((section, i) => (
            <div key={i} className="rounded-2xl p-5 border border-white/10 bg-white/[0.04]">
              <div className="flex items-center gap-3 mb-2.5">
                <span className={`w-9 h-9 rounded-full border flex items-center justify-center shrink-0 ${content.accentBg} ${content.accent}`}>
                  <section.icon size={16} />
                </span>
                <h2 className="text-white font-semibold text-sm">{section.heading}</h2>
              </div>
              <p className="text-white/65 text-sm leading-relaxed">{section.body}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
