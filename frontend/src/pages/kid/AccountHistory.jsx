import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ClipboardCheck, Wind, Gauge, Sparkles, Music } from 'lucide-react'
import { meAPI } from '../../api/client'

// One icon+color per entry kind, matching the "game" field the backend
// sends back (GET /me/history, routers/breathquest/kid_progress.py) —
// keeps this page dumb about game internals, just a lookup by name.
const GAME_STYLE = {
  assessment:      { icon: ClipboardCheck, color: 'text-sky',   bg: 'bg-sky/15' },
  BreathQuest:     { icon: Wind,           color: 'text-mint',  bg: 'bg-mint/15' },
  VoiceHurdleRace: { icon: Gauge,          color: 'text-ember', bg: 'bg-ember/15' },
  VaakMirror:      { icon: Sparkles,       color: 'text-brand-purple', bg: 'bg-brand-purple/15' },
  Chime:           { icon: Music,          color: 'text-brand-amber', bg: 'bg-brand-amber/15' },
}

function styleFor(entry) {
  return GAME_STYLE[entry.kind === 'assessment' ? 'assessment' : entry.game] || GAME_STYLE.Chime
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const days = Math.floor((now - d) / (1000 * 60 * 60 * 24))
  if (days === 0) return 'Today'
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days} days ago`
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined })
}

// Groups consecutive-by-day entries under one date heading, the way a
// kid thinks about "what did I do this week" rather than a flat list.
function groupByDay(entries) {
  const groups = []
  let lastLabel = null
  for (const entry of entries) {
    const label = formatDate(entry.date)
    if (label !== lastLabel) {
      groups.push({ label, items: [] })
      lastLabel = label
    }
    groups[groups.length - 1].items.push(entry)
  }
  return groups
}

export default function AccountHistory() {
  const navigate = useNavigate()
  const [entries, setEntries] = useState(null)
  const [status, setStatus] = useState('loading') // loading | ready | error

  const fetchHistory = () => {
    setStatus('loading')
    let cancelled = false
    meAPI.history()
      .then(({ data }) => { if (!cancelled) { setEntries(data); setStatus('ready') } })
      .catch(() => { if (!cancelled) setStatus('error') })
    return () => { cancelled = true }
  }

  useEffect(() => fetchHistory(), [])

  const groups = entries ? groupByDay(entries) : []

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #12142E 0%, #1E1E3F 100%)' }}>
      <div className="max-w-2xl mx-auto px-6 py-10">
        <button
          onClick={() => navigate('/play/account')}
          className="inline-flex items-center gap-1.5 text-white/40 hover:text-white text-sm mb-8 transition-colors"
        >
          <ArrowLeft size={15} /> Back to my account
        </button>

        <div className="mb-8">
          <h1 className="font-vm-display text-3xl font-bold text-white">My History</h1>
          <p className="text-white/40 mt-2">Every assessment and game, all in one place.</p>
        </div>

        {status === 'loading' && (
          <div className="text-center py-20 text-white/40">Loading your history…</div>
        )}

        {status === 'error' && (
          <div className="text-center py-20">
            <p className="text-white/50 mb-2">Couldn't load your history right now.</p>
            <button
              onClick={fetchHistory}
              className="text-white/60 hover:text-white text-sm underline underline-offset-2 transition-colors"
            >
              Try again
            </button>
          </div>
        )}

        {status === 'ready' && entries?.length === 0 && (
          <div className="text-center py-20">
            <p className="text-white/50 mb-1">Nothing here yet.</p>
            <p className="text-white/30 text-sm">Play a game or take your assessment to start your history!</p>
          </div>
        )}

        {status === 'ready' && groups.length > 0 && (
          <div className="space-y-8">
            {groups.map((group, gi) => (
              <div key={gi}>
                <p className="text-white/30 text-xs font-semibold uppercase tracking-wide mb-3">
                  {group.label}
                </p>
                <div className="space-y-2">
                  {group.items.map((entry, ei) => {
                    const { icon: Icon, color, bg } = styleFor(entry)
                    return (
                      <div
                        key={ei}
                        className="rounded-2xl p-4 border border-white/10 bg-white/5 flex items-center gap-4"
                      >
                        <div className={`w-10 h-10 rounded-full ${bg} flex items-center justify-center flex-shrink-0`}>
                          <Icon className={`w-5 h-5 ${color}`} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-white text-sm font-medium truncate">{entry.title}</p>
                          {entry.detail && (
                            <p className="text-white/40 text-xs mt-0.5">{entry.detail}</p>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
