import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingUp, Volume2, Sparkles, Mic, ArrowRight, Star } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { Avatar, Sidebar } from '../../components/ui'
import { KID_SIDEBAR_ITEMS } from '../../lib/kidSidebarItems'
import { KID_GAMES } from '../../lib/kidGames'
import { speak } from '../../lib/speech'
import { meAPI } from '../../api/client'

// Fixed positions so the starfield doesn't reshuffle on every render.
const STARS = [
  { top: '6%', left: '12%', size: 2, opacity: 0.5 },
  { top: '14%', left: '82%', size: 1.5, opacity: 0.4 },
  { top: '22%', left: '35%', size: 1, opacity: 0.35 },
  { top: '9%', left: '58%', size: 1.5, opacity: 0.45 },
  { top: '31%', left: '90%', size: 2, opacity: 0.3 },
  { top: '41%', left: '6%', size: 1, opacity: 0.4 },
  { top: '53%', left: '48%', size: 1.5, opacity: 0.25 },
  { top: '62%', left: '20%', size: 1, opacity: 0.4 },
  { top: '71%', left: '77%', size: 2, opacity: 0.35 },
  { top: '85%', left: '40%', size: 1, opacity: 0.3 },
  { top: '18%', left: '68%', size: 1, opacity: 0.3 },
  { top: '77%', left: '10%', size: 1.5, opacity: 0.35 },
]

function Starfield() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
      {STARS.map((s, i) => (
        <div
          key={i}
          className="absolute rounded-full bg-white motion-safe:animate-pulse-slow"
          style={{
            top: s.top,
            left: s.left,
            width: s.size,
            height: s.size,
            opacity: s.opacity,
            animationDelay: `${i * 0.4}s`,
          }}
        />
      ))}
      <div
        className="absolute -top-24 -left-16 w-96 h-96 rounded-full blur-3xl opacity-20"
        style={{ background: 'radial-gradient(circle, #FF9B54, transparent 70%)' }}
      />
      <div
        className="absolute top-1/3 -right-24 w-[28rem] h-[28rem] rounded-full blur-3xl opacity-[0.12]"
        style={{ background: 'radial-gradient(circle, #2FB8A6, transparent 70%)' }}
      />
      <div
        className="absolute -bottom-32 left-1/4 w-96 h-96 rounded-full blur-3xl opacity-[0.14]"
        style={{ background: 'radial-gradient(circle, #A78BFA, transparent 70%)' }}
      />
    </div>
  )
}

function CardMotif({ motif, accent }) {
  if (motif === 'flame') {
    return (
      <div className="absolute top-6 right-6 w-8 h-8 opacity-60 group-hover:opacity-100 transition-opacity
                      duration-300 motion-safe:animate-flicker" style={{ transformOrigin: 'bottom center' }}>
        <svg viewBox="0 0 24 24" fill="none">
          <path d="M12 1C12 1 4 10 4 18C4 23 8 27 12 27C16 27 20 23 20 18C20 10 12 1 12 1Z" fill={accent} />
        </svg>
      </div>
    )
  }
  if (motif === 'ripple') {
    return (
      <div className="absolute top-6 right-6 w-8 h-8 rounded-full border-2 opacity-50
                      group-hover:opacity-100 group-hover:scale-150 transition-all duration-500"
           style={{ borderColor: accent }} />
    )
  }
  return (
    <div className="absolute top-6 right-6 w-3 h-3 rounded-full opacity-60 group-hover:opacity-100
                    motion-safe:animate-pulse-slow transition-opacity duration-300"
         style={{ backgroundColor: accent }} />
  )
}

function GameIcon({ app, large }) {
  return (
    <div
      className={`relative flex items-center justify-center rounded-full shrink-0 transition-transform
                 duration-300 group-hover:scale-110 group-hover:-translate-y-0.5
                 ${large ? 'w-16 h-16 text-4xl' : 'w-14 h-14 text-3xl'}`}
      style={{
        background: `radial-gradient(circle at 35% 28%, ${app.accentSoft}, transparent 70%), rgba(255,255,255,0.03)`,
        boxShadow: `inset 0 0 0 1px ${app.accent}40, 0 0 22px -6px ${app.glow}`,
      }}
    >
      {app.emoji}
    </div>
  )
}

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

// Short, kid-readable "how long ago" for a world's last-played timestamp --
// deliberately coarse (today/yesterday/Nd ago/Nw ago) rather than an exact
// date, matching the rest of this page's encouraging, low-precision tone.
function timeAgo(iso) {
  if (!iso) return null
  const ms = Date.now() - new Date(iso).getTime()
  const days = Math.floor(ms / 86400000)
  if (days <= 0) return 'today'
  if (days === 1) return 'yesterday'
  if (days < 7) return `${days}d ago`
  const weeks = Math.floor(days / 7)
  return `${weeks}w ago`
}

// The small progress pill shown on each world card -- stars-with-a-cap
// where that concept exists (BreathQuest), a bare star count where it
// exists without a cap (Voice Hurdle Race), or just a play count for
// games with no per-level star system (Orpheus, Chime, Flashcards). Cards
// with zero recorded plays show nothing here, same as before this existed.
function ProgressPill({ app, s, accent }) {
  if (!s || (!s.plays && s.stars == null)) return null
  return (
    <div className="flex items-center gap-2 mt-2 text-xs">
      {s.stars != null ? (
        <span className="inline-flex items-center gap-1 font-semibold" style={{ color: accent }}>
          <Star size={11} fill="currentColor" />
          {s.stars}{s.max_stars ? `/${s.max_stars}` : ''}
        </span>
      ) : s.plays > 0 ? (
        <span className="text-white/35">{s.plays} play{s.plays === 1 ? '' : 's'}</span>
      ) : null}
      {s.last_played && (
        <span className="text-white/25">· {timeAgo(s.last_played)}</span>
      )}
    </div>
  )
}

export default function GamePicker() {
  const { patient, logout } = useAuth()
  const navigate = useNavigate()
  const [mounted, setMounted] = useState(false)
  const [summary, setSummary] = useState({})

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 30)
    return () => clearTimeout(t)
  }, [])

  // Per-world stars/plays/last-played for the cards below -- see
  // GameSummary on the backend (routers/breathquest/kid_progress.py).
  // Best-effort: a failed fetch just means cards render with no pill,
  // same as before this existed.
  useEffect(() => {
    meAPI.gamesSummary().then(({ data }) => setSummary(data)).catch(() => {})
  }, [])

  // Manual tap-to-hear only, no auto-play — see Play.jsx for why nav/menu
  // screens don't auto-speak while the actual games still do.
  const spokenGreeting = patient
    ? `${greeting()}, ${patient.first_name || 'friend'}! Pick a world to play in — each one starts the same way, take a breath.`
    : null
  const replayGreeting = () => { if (spokenGreeting) speak(spokenGreeting) }

  const lastRowCount = KID_GAMES.length % 3 || 3

  return (
    <div className="flex min-h-screen">
      <Sidebar role="kid" items={KID_SIDEBAR_ITEMS} name={patient?.first_name} onLogout={logout} />
      <div className="relative flex-1 overflow-hidden" style={{ background: 'linear-gradient(180deg, #12142E 0%, #1E1E3F 100%)' }}>
        <Starfield />

        <div className="relative flex items-center justify-between px-6 py-4 border-b border-white/10 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <Avatar avatar={patient?.avatar} photoUrl={patient?.avatar_photo_url} size="sm" />
            <div>
              <span className="font-display font-bold text-white">{patient?.first_name}</span>
              <span className="text-white/30 text-xs ml-2">#{patient?.player_code}</span>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <button onClick={() => navigate('/play/account')} className="flex items-center gap-1.5 text-white/40 hover:text-white hover:bg-white/5 text-sm transition-colors px-2.5 py-1.5 rounded-lg">
              <TrendingUp size={15} /> My Account
            </button>
            <button onClick={() => navigate('/assessment')} className="flex items-center gap-1.5 text-white/40 hover:text-white hover:bg-white/5 text-sm transition-colors px-2.5 py-1.5 rounded-lg">
              <Mic size={15} /> Assessment
            </button>
            <button onClick={() => navigate('/assessment/report')} className="flex items-center gap-1.5 text-white/40 hover:text-white hover:bg-white/5 text-sm transition-colors px-2.5 py-1.5 rounded-lg">
              <Sparkles size={15} /> My Results
            </button>
            <button onClick={logout} className="text-white/30 hover:text-white/60 text-sm transition-colors px-2.5 py-1.5 rounded-lg hover:bg-white/5 ml-1">
              Switch player
            </button>
          </div>
        </div>

        <div className="relative max-w-5xl mx-auto px-6 py-14">
          <div className="text-center mb-12">
            <div className="inline-block relative">
              <div className="absolute inset-0 rounded-full blur-xl opacity-40 scale-110" style={{ background: 'radial-gradient(circle, #A78BFA, transparent 70%)' }} />
              <Avatar avatar={patient?.avatar} photoUrl={patient?.avatar_photo_url} size="xl" />
            </div>
            <h1 className="font-vm-display text-4xl font-bold text-white mt-5">
              {greeting()}, {patient?.first_name || 'friend'}!
            </h1>
            <p className="text-white/40 mt-3 flex items-center justify-center gap-1.5">
              Pick a world to play in — each one starts the same way, take a breath 🌬️
              <button onClick={replayGreeting} className="text-white/25 hover:text-white/50 transition-colors" aria-label="Hear this again">
                <Volume2 className="w-3.5 h-3.5" />
              </button>
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {KID_GAMES.map((app, i) => {
              const isLastRow = i >= KID_GAMES.length - lastRowCount
              const isWide = lastRowCount === 2 && i === KID_GAMES.length - 1
              return (
                <button
                  key={app.id}
                  onClick={() => navigate(app.path)}
                  className={`group relative text-left rounded-3xl overflow-hidden transition-all duration-500
                             hover:-translate-y-1.5 focus-visible:outline-none focus-visible:ring-2
                             focus-visible:ring-white/70 focus-visible:ring-offset-2
                             focus-visible:ring-offset-[#12142E] ${isWide ? 'lg:col-span-2' : ''} ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}
                  style={{ transitionDelay: mounted ? `${i * 90}ms` : '0ms' }}
                >
                  <div
                    className={`relative h-full rounded-3xl border-2 transition-all duration-300 ${isWide ? 'p-6 flex items-center gap-6' : 'p-7'}`}
                    style={{
                      background: `linear-gradient(160deg, ${app.accentSoft} 0%, #1E1E3F 65%)`,
                      borderColor: 'rgba(255,255,255,0.08)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = app.accent + '55'
                      e.currentTarget.style.boxShadow = `0 12px 30px -8px ${app.glow}`
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'
                      e.currentTarget.style.boxShadow = 'none'
                    }}
                  >
                    <div className="absolute -bottom-8 -left-8 w-28 h-28 rounded-full blur-2xl opacity-40"
                         style={{ backgroundColor: app.accent }} />
                    <div
                      className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000 ease-out pointer-events-none"
                      style={{ background: `linear-gradient(100deg, transparent 40%, ${app.accent}22 50%, transparent 60%)` }}
                    />
                    <CardMotif motif={app.motif} accent={app.accent} />
                    {isWide ? (
                      <>
                        <GameIcon app={app} large />
                        <div className="relative flex-1 flex items-center justify-between gap-4">
                          <div>
                            <h3 className="font-vm-display font-bold text-white text-lg mb-1">{app.name}</h3>
                            <p className="text-white/45 text-xs leading-relaxed">{app.desc}</p>
                            <ProgressPill app={app} s={summary[app.id]} accent={app.accent} />
                          </div>
                          <span className="flex items-center gap-1 text-xs font-semibold shrink-0 transition-transform duration-300 group-hover:translate-x-1" style={{ color: app.accent }}>
                            {summary[app.id]?.plays > 0 ? 'Continue' : 'Play now'} <ArrowRight size={13} />
                          </span>
                        </div>
                      </>
                    ) : (
                      <div className="relative">
                        <div className="mb-4">
                          <GameIcon app={app} />
                        </div>
                        <h3 className="font-vm-display font-bold text-white text-lg mb-1.5">{app.name}</h3>
                        <p className="text-white/45 text-xs leading-relaxed">{app.desc}</p>
                        <ProgressPill app={app} s={summary[app.id]} accent={app.accent} />
                        <span className="flex items-center gap-1 text-xs font-semibold transition-transform duration-300 group-hover:translate-x-1 mt-6" style={{ color: app.accent }}>
                          {summary[app.id]?.plays > 0 ? 'Continue' : 'Play now'} <ArrowRight size={13} />
                        </span>
                      </div>
                    )}
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
