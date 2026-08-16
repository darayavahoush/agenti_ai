import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, Calendar, Star, Sparkles, Heart, LogOut, CreditCard } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { Avatar, Card, StatCard, Sidebar } from '../../components/ui'
import { parentAPI } from '../../api/client'

function formatDate(iso) {
  if (!iso) return 'Not yet played'
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

// Parent-facing dashboard, reading GET /parent/progress — a fully-built
// backend endpoint (routers/parent.py) that already existed with zero
// frontend consumer, same situation as kid_progress.py before MyProgress.jsx.
// Deliberately trend-level, matching what the backend itself already
// decided to expose: no raw per-attempt scores, no avg_breath_strength
// (backend sends that field back as null on purpose -- see the comment on
// LevelProgress in parent.py), no clinical notes. That's therapist-only,
// via a completely separate dashboard.py + therapist token.
export default function ParentDashboard() {
  const { parent, logout } = useAuth()
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('loading') // loading | ready | error
  const [activity, setActivity] = useState(null)

  useEffect(() => {
    let cancelled = false
    parentAPI.progress()
      .then(({ data }) => { if (!cancelled) { setData(data); setStatus('ready') } })
      .catch(() => { if (!cancelled) setStatus('error') })
    parentAPI.guidedActivity()
      .then(({ data }) => { if (!cancelled) setActivity(data) })
      .catch(err => console.error('Failed to load guided activity:', err))
    return () => { cancelled = true }
  }, [])

  const starPct = data ? Math.min(100, Math.round((data.total_stars / Math.max(1, data.max_possible_stars)) * 100)) : 0
  const trend = data?.improvement_trend

  return (
    <div className="min-h-screen bg-ink relative flex">
      {/* Ambient glow header — same elevated-dashboard language as the
          therapist side, in the parent flow's own coral/mint accent pair
          instead of teal/green. */}
      <div className="absolute top-0 left-0 w-full h-80 overflow-hidden pointer-events-none">
        <div className="absolute -top-32 -left-24 w-[28rem] h-[28rem] rounded-full bg-coral/[0.08] blur-[100px]" />
        <div className="absolute -top-40 right-0 w-[26rem] h-[26rem] rounded-full bg-mint/[0.06] blur-[100px]" />
      </div>

      <Sidebar
        role="parent"
        items={[
          { label: 'Progress', icon: TrendingUp, to: '/parent/dashboard' },
          { label: 'Billing', icon: CreditCard, to: '/parent/billing' },
        ]}
        name={(data?.child_first_name || parent?.child_first_name) ? `${data?.child_first_name || parent?.child_first_name}'s Progress` : undefined}
        onLogout={logout}
      />

      <div className="relative flex-1 min-w-0 max-w-3xl mx-auto px-6 py-10">
        {status === 'loading' && (
          <div className="animate-pulse">
            <div className="flex items-center gap-3 mb-8">
              <div className="w-8 h-8 rounded-full bg-white/[0.06]" />
              <div className="h-3 w-40 rounded-full bg-white/[0.06]" />
            </div>
            <div className="grid grid-cols-3 gap-4 mb-6">
              {Array.from({ length: 3 }, (_, i) => (
                <div key={i} className="rounded-2xl bg-white/[0.04] border border-white/[0.06] p-4 h-24" />
              ))}
            </div>
            <div className="rounded-2xl bg-white/[0.04] border border-white/[0.06] h-20 mb-8" />
            <div className="h-3 w-28 rounded-full bg-white/[0.06] mb-3" />
            <div className="flex flex-col gap-2.5">
              {Array.from({ length: 4 }, (_, i) => (
                <div key={i} className="rounded-2xl bg-white/[0.04] border border-white/[0.06] h-16" />
              ))}
            </div>
          </div>
        )}

        {status === 'error' && (
          <div className="text-center py-20">
            <p className="text-paper/50 mb-2">Couldn't load progress right now.</p>
            <p className="text-paper/30 text-sm">Try again in a bit!</p>
          </div>
        )}

        {status === 'ready' && data && (
          <>
            {/* Weekly summary — dense numbers/chips only, no narrative prose.
                stats/highlights both come from the rule-based (no LLM)
                generator dashboard.py already builds for therapists too. */}
            <Card className="border-mint/20 mb-6">
              <p className="font-mono text-xs uppercase tracking-widest text-mint mb-4">This week</p>
              <div className="grid grid-cols-3 gap-x-4 gap-y-4 mb-5">
                {[
                  ['BreathQuest', data.weekly_summary.stats.bq_sessions],
                  ['— completed', data.weekly_summary.stats.bq_completed],
                  ['Chime attempts', data.weekly_summary.stats.chime_attempts],
                  ['Assignments done', data.weekly_summary.stats.assignments_completed],
                  ['Assignments overdue', data.weekly_summary.stats.assignments_overdue],
                  ['Goals open', data.weekly_summary.stats.goals_open],
                  ['Goals achieved', data.weekly_summary.stats.goals_achieved_total],
                  ['Practice days', `${data.weekly_summary.stats.home_practice_days}/7`],
                  ['Practice minutes', data.weekly_summary.stats.home_practice_minutes],
                ].map(([label, value], i) => (
                  <div key={i}>
                    <p className="font-display text-xl font-bold text-paper leading-none tracking-tight">{value}</p>
                    <p className="text-paper/40 text-[11px] leading-tight mt-1.5">{label}</p>
                  </div>
                ))}
              </div>
              {data.weekly_summary.highlights?.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {data.weekly_summary.highlights.map((h, i) => (
                    <span key={i} className="text-xs font-semibold px-3 py-1 rounded-full bg-mint/15 text-mint-light border border-mint/25">
                      {h}
                    </span>
                  ))}
                </div>
              )}
            </Card>

            {/* Try this with your child — guided activity from the 50-idea
                library, targeted at their weakest recent sound if we have
                enough data (GET /parent/guided-activity). */}
            {activity && (
              <Card className="border-coral/25 mb-6">
                <div className="flex items-center gap-2 mb-3">
                  <Heart size={16} className="text-coral-light" />
                  <p className="font-mono text-xs uppercase tracking-widest text-coral-light">
                    Try this with your child today
                  </p>
                </div>
                <p className="font-display text-lg font-bold text-paper mb-1">{activity.idea.title}</p>
                <p className="text-paper/60 text-sm leading-relaxed mb-2">{activity.idea.description}</p>
                <p className="text-paper/35 text-xs italic">{activity.reason}</p>
              </Card>
            )}

            {/* Top stats row */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <StatCard icon={Sparkles} accent="#FAC775" value={data.total_sessions} label="sessions played" />
              <StatCard icon={Star} accent="#FAC775" value={`${Math.round(data.completion_rate * 100)}%`} label="sessions completed" />
              {trend == null ? (
                <StatCard icon={Calendar} accent="#6B7280" value="—" label="not enough data yet" />
              ) : (
                <StatCard
                  icon={trend >= 0 ? TrendingUp : TrendingDown}
                  accent={trend >= 0 ? '#2FB8A6' : '#F0604A'}
                  value={`${trend >= 0 ? '+' : ''}${trend}`}
                  label="star trend"
                />
              )}
            </div>

            {/* Total stars bar -- now BreathQuest + VoiceHurdleRace combined,
                the two games that actually have a stars concept. */}
            <Card className="mb-8">
              <div className="flex items-center justify-between mb-3">
                <span className="text-paper/60 text-sm font-medium">Total stars</span>
                <span className="text-paper/40 text-xs">{data.total_stars} / {data.max_possible_stars}</span>
              </div>
              <div className="h-3 rounded-full bg-white/[0.06] overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-brand-amber to-ember rounded-full transition-[width] duration-700"
                  style={{ width: `${starPct}%` }}
                />
              </div>
            </Card>

            {/* Games & Levels -- BreathQuest + VoiceHurdleRace merged, since
                both are level_id/level_name/stars shaped. avg_breath_strength
                is still never shown here on purpose. */}
            <h2 className="font-display text-lg font-bold text-paper mb-3">Games & levels</h2>
            <div className="flex flex-col gap-2.5 mb-8">
              {[...(data.categories?.breathquest ?? []), ...(data.categories?.voicehurdlerace ?? [])].map((cat, i) => (
                <Card key={i} className="flex items-center justify-between gap-4 py-4">
                  <div>
                    <p className="text-paper text-sm font-semibold">{cat.category_name}</p>
                    <p className="text-paper/35 text-xs mt-0.5">
                      {cat.attempts} attempt{cat.attempts === 1 ? '' : 's'} · last played {formatDate(cat.last_played)}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {Array.from({ length: 3 }, (_, j) => (
                      <span key={j} className="text-lg" style={{ color: j < (cat.stars ?? 0) ? '#FAC775' : 'rgba(255,255,255,0.12)' }}>
                        ★
                      </span>
                    ))}
                  </div>
                </Card>
              ))}
            </div>

            {/* VaakMirror -- no stars concept, shown as pass-rate instead. */}
            {data.categories?.vaakmirror?.length > 0 && (
              <>
                <h2 className="font-display text-lg font-bold text-paper mb-3">VaakMirror</h2>
                <div className="flex flex-col gap-2.5 mb-8">
                  {data.categories.vaakmirror.map((cat, i) => (
                    <Card key={i} className="flex items-center justify-between gap-4 py-4">
                      <div>
                        <p className="text-paper text-sm font-semibold">
                          {cat.category_name.split('_').map(w => w[0].toUpperCase() + w.slice(1)).join(' ')}
                        </p>
                        <p className="text-paper/35 text-xs mt-0.5">
                          {cat.attempts} attempt{cat.attempts === 1 ? '' : 's'} · last played {formatDate(cat.last_played)}
                        </p>
                      </div>
                      <p className="text-paper text-sm font-semibold shrink-0">{cat.accuracy_pct}%</p>
                    </Card>
                  ))}
                </div>
              </>
            )}

            {/* Flashcards -- per-phoneme mastery, no stars/levels either. */}
            {data.categories?.flashcards?.length > 0 && (
              <>
                <h2 className="font-display text-lg font-bold text-paper mb-3">Flashcards</h2>
                <div className="flex flex-col gap-2.5 mb-8">
                  {data.categories.flashcards.map((cat, i) => (
                    <Card key={i} className="flex items-center justify-between gap-4 py-4">
                      <div>
                        <p className="text-paper text-sm font-semibold">/{cat.category_name}/</p>
                        <p className="text-paper/35 text-xs mt-0.5">
                          {cat.attempts} attempt{cat.attempts === 1 ? '' : 's'} · last played {formatDate(cat.last_played)}
                        </p>
                      </div>
                      <p className="text-paper text-sm font-semibold shrink-0">{cat.accuracy_pct}%</p>
                    </Card>
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  )
}
