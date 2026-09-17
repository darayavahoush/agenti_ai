import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Flame, Star, Calendar, CloudOff, Sparkles, Check, Target, Trophy, Compass } from 'lucide-react'
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
  // Calendar and goal load independently of /me/progress: they're additions
  // to this page, not prerequisites for it, so a slow or failing one hides
  // its own card rather than taking the whole page down with it.
  const [calendar, setCalendar] = useState(null)
  const [goal, setGoal] = useState(null)
  const [quests, setQuests] = useState([])
  const [companion, setCompanion] = useState(null)
  const [extrasStatus, setExtrasStatus] = useState('loading') // loading | ready | error

  const fetchProgress = () => {
    setStatus('loading')
    setExtrasStatus('loading')
    let cancelled = false
    meAPI.progress()
      .then(({ data }) => { if (!cancelled) { setProgress(data); setStatus('ready') } })
      .catch(() => { if (!cancelled) setStatus('error') })

    Promise.allSettled([meAPI.calendar(), meAPI.goal(), meAPI.quests(), meAPI.companion()])
      .then(([cal, gl, qs, cp]) => {
        if (cancelled) return
        setCalendar(cal.status === 'fulfilled' ? cal.value.data : null)
        // /me/goal legitimately returns null when there's no goal yet or no
        // computable progress -- that's a "show nothing", not an error.
        setGoal(gl.status === 'fulfilled' ? gl.value.data : null)
        setQuests(qs.status === 'fulfilled' ? qs.value.data : [])
        setCompanion(cp.status === 'fulfilled' ? cp.value.data : null)
        setExtrasStatus(cal.status === 'fulfilled' ? 'ready' : 'error')
      })
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
                <Avatar
                  avatar={companion?.equipped?.kind === 'avatar' ? companion.equipped.item_id : progress.avatar}
                  size="xl"
                  accessory={companion?.equipped?.kind === 'accessory' ? companion.equipped.item_id : null}
                />
              </div>
              <h1 className="font-vm-display text-3xl font-bold text-white mt-5">
                {progress.first_name}'s Progress
              </h1>
              <p className="text-white/40 mt-2">Look how far you've come! 🎉</p>
              {companion?.next && (
                <p className="text-white/35 text-xs mt-2">
                  Next: <span className="text-white/55 font-medium">{companion.next.label}</span> at a {companion.next.streak_days}-day streak
                  {progress.current_streak_days > 0 && ` (${Math.min(progress.current_streak_days, companion.next.streak_days)}/${companion.next.streak_days})`}
                </p>
              )}
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

            {/* ---- This week's practice calendar ---------------------- */}
            {extrasStatus === 'loading' && (
              <div className="rounded-3xl p-6 border border-white/10 bg-white/5 mb-6 animate-pulse">
                <div className="h-4 w-40 rounded-full bg-white/10" />
                <div className="flex justify-between gap-2 mt-6">
                  {[0, 1, 2, 3, 4, 5, 6].map((i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-2">
                      <div className="h-2.5 w-6 rounded-full bg-white/[0.06]" />
                      <div className="w-11 h-11 rounded-2xl bg-white/10" />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {calendar && (
              <div
                className="relative rounded-3xl p-6 border border-white/10 bg-white/5 mb-6 overflow-hidden
                           animate-[popIn_0.5s_ease-out_backwards]"
                style={{ animationDelay: '320ms' }}
              >
                <div
                  className="pointer-events-none absolute -top-16 -right-10 w-48 h-48 rounded-full blur-3xl opacity-40"
                  style={{ background: 'radial-gradient(circle, rgba(47,184,166,0.35), transparent 70%)' }}
                />

                <div className="relative flex items-center justify-between mb-5">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-mint" />
                    <span className="text-white/70 text-sm font-semibold">This week</span>
                  </div>
                  <span className="text-white/40 text-xs tabular-nums">
                    {calendar.days_practiced} / {calendar.target_days} days
                  </span>
                </div>

                <div className="relative flex justify-between gap-1.5 sm:gap-2">
                  {calendar.days.map((day, i) => (
                    <div key={day.date} className="flex-1 flex flex-col items-center gap-2 min-w-0">
                      <span className={`text-[10px] font-semibold uppercase tracking-wide
                                        ${day.is_today ? 'text-white/80' : 'text-white/30'}`}>
                        {day.label[0]}
                      </span>
                      <div
                        className={`w-full aspect-square max-w-[52px] rounded-2xl flex items-center justify-center
                                    transition-all duration-300 animate-[popIn_0.4s_ease-out_backwards]
                                    ${day.practiced
                                      ? 'bg-gradient-to-br from-mint to-brand-amber shadow-lg shadow-mint/20 hover:scale-110 hover:-rotate-6'
                                      : day.is_future
                                        ? 'bg-white/[0.04] border border-dashed border-white/10'
                                        : 'bg-white/[0.07] border border-white/10'}
                                    ${day.is_today ? 'ring-2 ring-white/60 ring-offset-2 ring-offset-transparent' : ''}`}
                        style={{ animationDelay: `${360 + i * 60}ms` }}
                        title={day.practiced ? 'You practiced!' : day.is_future ? 'Coming up' : 'No practice yet'}
                      >
                        {day.practiced
                          ? <Check className="w-5 h-5 text-[#12142E]" strokeWidth={3.5} />
                          : day.is_today
                            ? <span className="w-2 h-2 rounded-full bg-white/70 animate-pulse" />
                            : <span className="w-1.5 h-1.5 rounded-full bg-white/20" />}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="relative mt-5">
                  <div className="h-2.5 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-mint to-brand-amber transition-[width] duration-700"
                      style={{ width: `${Math.min(100, Math.round((calendar.days_practiced / Math.max(1, calendar.target_days)) * 100))}%` }}
                    />
                  </div>
                  <p className={`text-center text-xs mt-3 font-medium
                                 ${calendar.target_met ? 'text-mint' : 'text-white/50'}`}>
                    {calendar.message}
                  </p>
                </div>
              </div>
            )}

            {/* ---- Latest goal ----------------------------------------- */}
            {goal && (
              <div
                className="relative rounded-3xl p-6 border border-white/10 bg-white/5 mb-6 overflow-hidden
                           animate-[popIn_0.5s_ease-out_backwards]"
                style={{ animationDelay: '420ms' }}
              >
                <div
                  className="pointer-events-none absolute -bottom-16 -left-10 w-48 h-48 rounded-full blur-3xl opacity-40"
                  style={{ background: 'radial-gradient(circle, rgba(250,199,117,0.3), transparent 70%)' }}
                />

                <div className="relative flex items-start gap-4">
                  <div className={`shrink-0 w-12 h-12 rounded-2xl flex items-center justify-center
                                   ${goal.achieved ? 'bg-brand-amber/20' : 'bg-mint/15'}`}>
                    {goal.achieved
                      ? <Trophy className="w-6 h-6 text-brand-amber" fill="currentColor" fillOpacity={0.3} />
                      : <Target className="w-6 h-6 text-mint" />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-white/40 text-[10px] font-semibold uppercase tracking-wider">
                      Your goal right now
                    </p>
                    <h2 className="font-vm-display text-xl font-bold text-white mt-0.5 truncate">
                      {goal.title}
                    </h2>
                    <p className="text-white/45 text-xs mt-1">{goal.blurb}</p>
                  </div>
                  {goal.days_left !== null && goal.days_left !== undefined && !goal.achieved && (
                    <span className="shrink-0 text-[10px] font-semibold text-white/50 bg-white/10 rounded-full px-2.5 py-1">
                      {goal.days_left === 0 ? 'Last day' : `${goal.days_left}d left`}
                    </span>
                  )}
                </div>

                <div className="relative mt-5">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-white/50 text-xs">Progress</span>
                    <span className="text-white font-vm-display text-sm font-bold tabular-nums">
                      {goal.progress_pct}%
                    </span>
                  </div>
                  <div className="h-3.5 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-mint via-brand-amber to-ember
                                 bg-[length:200%_100%] animate-[shimmer_2.5s_linear_infinite]
                                 transition-[width] duration-700"
                      style={{ width: `${Math.max(3, goal.progress_pct)}%` }}
                    />
                  </div>
                </div>

                <p className="relative text-white/70 text-sm font-medium mt-4">{goal.encouragement}</p>
                <div className="relative mt-3 flex items-start gap-2 rounded-2xl bg-white/[0.04] border border-white/10 px-3.5 py-2.5">
                  <Sparkles className="w-3.5 h-3.5 text-brand-amber shrink-0 mt-0.5" />
                  <p className="text-white/50 text-xs leading-relaxed">{goal.looking_forward}</p>
                </div>
              </div>
            )}

            {/* ---- This week's quests ----------------------------------- */}
            {quests.length > 0 && (
              <div
                className="relative rounded-3xl p-6 border border-white/10 bg-white/5 mb-6 overflow-hidden
                           animate-[popIn_0.5s_ease-out_backwards]"
                style={{ animationDelay: '480ms' }}
              >
                <p className="text-white/40 text-[10px] font-semibold uppercase tracking-wider mb-4">
                  This week's quests
                </p>
                <div className="flex flex-col gap-4">
                  {quests.map((quest) => (
                    <div key={quest.id} className="flex items-center gap-4">
                      <div className={`shrink-0 w-10 h-10 rounded-2xl flex items-center justify-center
                                       ${quest.complete ? 'bg-mint/20' : 'bg-white/10'}`}>
                        {quest.complete
                          ? <Check className="w-5 h-5 text-mint" />
                          : <Compass className="w-5 h-5 text-white/50" />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-white text-sm font-semibold truncate">{quest.title}</p>
                        <p className="text-white/45 text-xs mt-0.5">{quest.description}</p>
                        <div className="h-2 rounded-full bg-white/10 overflow-hidden mt-2">
                          <div
                            className={`h-full rounded-full transition-[width] duration-700
                                       ${quest.complete ? 'bg-mint' : 'bg-brand-amber'}`}
                            style={{ width: `${Math.max(6, Math.round((quest.progress / Math.max(1, quest.target)) * 100))}%` }}
                          />
                        </div>
                      </div>
                      <span className="shrink-0 text-white/50 text-xs font-semibold tabular-nums">
                        {quest.progress}/{quest.target}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

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
