import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, Calendar, Star, Sparkles, Heart, LogOut, CreditCard, Settings } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { Avatar, Card, StatCard, Sidebar } from '../../components/ui'
import { useNavigate } from 'react-router-dom'
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
  const { parent, logout, deleteParentAccount } = useAuth()
  const navigate = useNavigate()
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
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
          { label: 'Settings', icon: Settings, to: '/parent/settings' },
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
            {/* Today's difficulty recommendation -- same adaptive-difficulty
                agent decision therapists already see, now surfaced for
                parents too. Only renders when there's an actual decision
                on file (recommended_action is null otherwise). */}
            {data.recommended_action && (
              <Card className="border-brand-amber/25 mb-6 flex items-center gap-3">
                <span className="text-xl">
                  {data.recommended_action === 'raise' ? '🔼' : data.recommended_action === 'lower' ? '🔽' : '➡️'}
                </span>
                <div>
                  <p className="text-paper text-sm font-semibold">
                    Today's difficulty: {data.recommended_action === 'raise' ? 'stepped up' : data.recommended_action === 'lower' ? 'eased back' : 'holding steady'}
                  </p>
                  {data.recommendation_message && (
                    <p className="text-paper/40 text-xs mt-0.5">{data.recommendation_message}</p>
                  )}
                </div>
              </Card>
            )}

            {/* Weekly summary — dense numbers/chips only, no narrative prose.
                stats/highlights both come from the rule-based (no LLM)
                generator dashboard.py already builds for therapists too. */}
            <Card className="border-mint/20 mb-6">
              <div className="flex items-center justify-between mb-4">
                <p className="font-mono text-xs uppercase tracking-widest text-mint">This week</p>
                {/* Transparency note -- this summary is deterministic, built
                    from actual session data, not an LLM guessing. Worth
                    saying explicitly for an audience wary of AI summaries. */}
                <span className="group relative">
                  <span className="text-paper/25 text-xs cursor-help">ⓘ How we write this</span>
                  <span className="absolute right-0 top-full mt-1 w-56 rounded-xl bg-ink border border-white/10
                                    p-3 text-paper/60 text-xs leading-relaxed opacity-0 group-hover:opacity-100
                                    pointer-events-none transition-opacity z-20">
                    Generated from your child's actual session data — not AI guessing. Same numbers every time, for the same week.
                  </span>
                </span>
              </div>
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

            {/* Breath-consistency trend -- session-level data that was never
                aggregated for parents before now. Only shows once there's
                enough data to be meaningful. */}
            {data.avg_breath_consistency != null && (
              <Card className="mb-8 flex items-center justify-between">
                <span className="text-paper/60 text-sm font-medium">Breath consistency</span>
                <span className="text-mint-light text-sm font-semibold">
                  {Math.round(data.avg_breath_consistency * 100)}%
                </span>
              </Card>
            )}

            {/* BreathQuest -- always renders all 6 fixed levels regardless
                of data (see bq_categories loop over LEVEL_NAMES server-side),
                so this section alone was never the empty-state problem. */}
            <h2 className="font-display text-lg font-bold text-paper mb-3">BreathQuest</h2>
            <div className="flex flex-col gap-2.5 mb-8">
              {(data.categories?.breathquest ?? []).map((cat, i) => (
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

            {/* VoiceHurdleRace -- split out of the old merged BreathQuest+VHR
                list. Its category list is built from actual session rows
                (vhr_by_level server-side), so on zero sessions it was
                silently contributing nothing to the merged list and
                vanishing -- same always-visible + empty-state treatment as
                VaakMirror/Flashcards below. */}
            <h2 className="font-display text-lg font-bold text-paper mb-3">VoiceHurdleRace</h2>
            <div className="flex flex-col gap-2.5 mb-8">
              {data.categories?.voicehurdlerace?.length > 0 ? (
                data.categories.voicehurdlerace.map((cat, i) => (
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
                ))
              ) : (
                <Card className="py-4">
                  <p className="text-paper/40 text-sm">Hasn't tried VoiceHurdleRace yet.</p>
                </Card>
              )}
            </div>

            {/* VaakMirror -- no stars concept, shown as pass-rate instead.
                Always shown, even with no sessions yet -- BreathQuest's
                fixed level list always renders something, so a bare
                empty-array games disappearing entirely made the app look
                BreathQuest-only rather than just "not tried yet". */}
            <h2 className="font-display text-lg font-bold text-paper mb-3">VaakMirror</h2>
            <div className="flex flex-col gap-2.5 mb-8">
              {data.categories?.vaakmirror?.length > 0 ? (
                data.categories.vaakmirror.map((cat, i) => (
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
                ))
              ) : (
                <Card className="py-4">
                  <p className="text-paper/40 text-sm">Hasn't tried VaakMirror yet.</p>
                </Card>
              )}
            </div>

            {/* Flashcards -- per-phoneme mastery, no stars/levels either.
                Same always-visible treatment as VaakMirror above. */}
            <h2 className="font-display text-lg font-bold text-paper mb-3">Flashcards</h2>
            <div className="flex flex-col gap-2.5 mb-8">
              {data.categories?.flashcards?.length > 0 ? (
                data.categories.flashcards.map((cat, i) => (
                  <Card key={i} className="flex items-center justify-between gap-4 py-4">
                    <div>
                      <p className="text-paper text-sm font-semibold">/{cat.category_name}/</p>
                      <p className="text-paper/35 text-xs mt-0.5">
                        {cat.attempts} attempt{cat.attempts === 1 ? '' : 's'} · last played {formatDate(cat.last_played)}
                      </p>
                    </div>
                    <p className="text-paper text-sm font-semibold shrink-0">{cat.accuracy_pct}%</p>
                  </Card>
                ))
              ) : (
                <Card className="py-4">
                  <p className="text-paper/40 text-sm">Hasn't tried Flashcards yet.</p>
                </Card>
              )}
            </div>

            {/* Chime -- new category, previously only surfaced as a single
                aggregate number (chime_attempts) in the weekly stats grid
                with no per-sound breakdown. Same pass-rate treatment as
                VaakMirror/Flashcards since Chime has no stars concept. */}
            <h2 className="font-display text-lg font-bold text-paper mb-3">Chime</h2>
            <div className="flex flex-col gap-2.5 mb-8">
              {data.categories?.chime?.length > 0 ? (
                data.categories.chime.map((cat, i) => (
                  <Card key={i} className="flex items-center justify-between gap-4 py-4">
                    <div>
                      <p className="text-paper text-sm font-semibold">/{cat.category_name}/</p>
                      <p className="text-paper/35 text-xs mt-0.5">
                        {cat.attempts} attempt{cat.attempts === 1 ? '' : 's'} · last played {formatDate(cat.last_played)}
                      </p>
                    </div>
                    <p className="text-paper text-sm font-semibold shrink-0">{cat.accuracy_pct}%</p>
                  </Card>
                ))
              ) : (
                <Card className="py-4">
                  <p className="text-paper/40 text-sm">Hasn't tried Chime yet.</p>
                </Card>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
