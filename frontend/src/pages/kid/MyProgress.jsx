import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Flame, Star, Calendar, CloudOff, Sparkles } from 'lucide-react'
import { Avatar, Button } from '../../components/ui'
import { meAPI } from '../../api/client'

// Kid-facing progress view. The backend endpoint this reads from
// (GET /me/progress, routers/kid_progress.py) already existed -- cross-game
// totals, weekly play count, a streak -- it just never had a page to show
// it on. Deliberately keeps the backend's own framing: no raw scores, no
// per-level breakdown, no clinical language, just numbers a kid can be
// proud of.
export default function MyProgress() {
  const navigate = useNavigate()
  const [progress, setProgress] = useState(null)
  const [status, setStatus] = useState('loading') // loading | ready | error

  const fetchProgress = () => {
    setStatus('loading')
    let cancelled = false
    meAPI.progress()
      .then(({ data }) => { if (!cancelled) { setProgress(data); setStatus('ready') } })
      .catch(() => { if (!cancelled) setStatus('error') })
    return () => { cancelled = true }
  }

  useEffect(() => fetchProgress(), [])

  const starPct = progress ? Math.min(100, Math.round((progress.total_stars / Math.max(1, progress.max_possible_stars)) * 100)) : 0

  const stats = progress ? [
    {
      key: 'streak', icon: Flame, color: 'ember', value: progress.current_streak_days,
      label: `day${progress.current_streak_days === 1 ? '' : 's'} in a row`,
    },
    {
      key: 'week', icon: Calendar, color: 'mint', value: progress.games_played_this_week,
      label: `game${progress.games_played_this_week === 1 ? '' : 's'} this week`,
    },
    {
      key: 'stars', icon: Star, color: 'brand-amber', value: progress.total_stars,
      label: 'total stars', fill: true,
    },
  ] : []

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #12142E 0%, #1E1E3F 100%)' }}>
      <div className="max-w-2xl mx-auto px-6 py-10">
        <button
          onClick={() => navigate('/play')}
          className="inline-flex items-center gap-1.5 text-white/40 hover:text-white text-sm mb-8 transition-colors"
        >
          <ArrowLeft size={15} /> Back to games
        </button>

        {status === 'loading' && (
          <div aria-label="Loading your progress">
            <div className="text-center mb-10 flex flex-col items-center">
              <div className="w-20 h-20 rounded-full bg-white/10 animate-pulse" />
              <div className="h-7 rounded-full bg-white/10 w-48 mt-5 animate-pulse" />
              <div className="h-4 rounded-full bg-white/[0.06] w-32 mt-3 animate-pulse" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="rounded-2xl p-6 text-center border border-white/10 bg-white/5 animate-pulse"
                  style={{ animationDelay: `${i * 120}ms` }}
                >
                  <div className="w-12 h-12 rounded-full bg-white/10 mx-auto mb-3" />
                  <div className="h-7 rounded-full bg-white/10 w-10 mx-auto" />
                  <div className="h-2.5 rounded-full bg-white/[0.06] w-16 mx-auto mt-2" />
                </div>
              ))}
            </div>
          </div>
        )}

        {status === 'error' && (
          <div className="text-center py-16 flex flex-col items-center">
            <div className="w-14 h-14 rounded-full bg-brand-coral/15 flex items-center justify-center mb-5">
              <CloudOff className="w-6 h-6 text-brand-coral" />
            </div>
            <p className="text-white/70 font-medium mb-1">Couldn't load your progress</p>
            <p className="text-white/40 text-sm mb-6">Check your connection and give it another try.</p>
            <Button variant="ghost" size="sm" onClick={fetchProgress}>Try again</Button>
          </div>
        )}

        {status === 'ready' && progress && (
          <>
            <div className="text-center mb-10 animate-[fadeIn_0.5s_ease-out]">
              <div className="inline-block animate-[bounce_2.5s_ease-in-out_infinite]">
                <Avatar avatar={progress.avatar} size="xl" />
              </div>
              <h1 className="font-vm-display text-3xl font-bold text-white mt-5">
                {progress.first_name}'s Progress
              </h1>
              <p className="text-white/40 mt-2">Look how far you've come! 🎉</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
              {stats.map(({ key, icon: Icon, color, value, label, fill }, i) => (
                <div
                  key={key}
                  className="group rounded-2xl p-6 text-center border border-white/10 bg-white/5
                             transition-all duration-300 hover:-translate-y-1 hover:scale-[1.03]
                             hover:border-white/20 hover:shadow-lg hover:shadow-white/5
                             animate-[popIn_0.5s_ease-out_backwards]"
                  style={{ animationDelay: `${i * 100}ms` }}
                >
                  <div className={`w-12 h-12 rounded-full bg-${color}/15 flex items-center justify-center mx-auto mb-3
                                    transition-transform duration-300 group-hover:scale-110 group-hover:rotate-[-8deg]`}>
                    <Icon className={`w-6 h-6 text-${color} group-hover:animate-[wiggle_0.5s_ease-in-out]`}
                      fill={fill ? 'currentColor' : 'none'} fillOpacity={fill ? 0.3 : undefined} />
                  </div>
                  <p className="font-vm-display text-3xl font-bold text-white tabular-nums">{value}</p>
                  <p className="text-white/40 text-xs mt-1">{label}</p>
                </div>
              ))}
            </div>

            <div className="relative rounded-2xl p-6 border border-white/10 bg-white/5 overflow-hidden">
              <div className="flex items-center justify-between mb-2">
                <span className="text-white/60 text-sm font-medium">Stars earned</span>
                <span className="text-white/40 text-xs">
                  {progress.total_stars} / {progress.max_possible_stars}
                </span>
              </div>
              <div className="h-4 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-brand-amber via-ember to-brand-amber
                             bg-[length:200%_100%] rounded-full transition-[width] duration-700
                             animate-[shimmer_2s_linear_infinite]"
                  style={{ width: `${starPct}%` }}
                />
              </div>

              {starPct === 100 && (
                <div className="relative mt-3 text-center">
                  <p className="text-brand-amber text-xs font-semibold flex items-center justify-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 animate-[spin_3s_linear_infinite]" />
                    You've earned every star -- amazing!
                    <Sparkles className="w-3.5 h-3.5 animate-[spin_3s_linear_infinite_reverse]" />
                  </p>
                  <div className="pointer-events-none absolute inset-0 -top-4">
                    {['🎉', '✨', '⭐️', '🎊', '✨'].map((e, i) => (
                      <span
                        key={i}
                        className="absolute text-lg animate-[confettiFall_1.8s_ease-in_forwards]"
                        style={{ left: `${10 + i * 20}%`, animationDelay: `${i * 120}ms` }}
                      >
                        {e}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {progress.current_streak_days === 0 && (
              <p className="text-white/30 text-xs text-center mt-8 animate-pulse">
                Play a game today to start a new streak! 🔥
              </p>
            )}
          </>
        )}
      </div>

      <style>{`
        @keyframes popIn {
          0% { opacity: 0; transform: translateY(12px) scale(0.95); }
          100% { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes fadeIn {
          0% { opacity: 0; transform: translateY(-6px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        @keyframes wiggle {
          0%, 100% { transform: rotate(0deg); }
          25% { transform: rotate(-10deg); }
          75% { transform: rotate(10deg); }
        }
        @keyframes shimmer {
          0% { background-position: 0% 0%; }
          100% { background-position: 200% 0%; }
        }
        @keyframes confettiFall {
          0% { opacity: 0; transform: translateY(0) rotate(0deg); }
          20% { opacity: 1; }
          100% { opacity: 0; transform: translateY(40px) rotate(180deg); }
        }
      `}</style>
    </div>
  )
}
