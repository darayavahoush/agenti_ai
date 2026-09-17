import { useEffect, useState } from 'react'
import {
  TrendingUp, TrendingDown, Calendar, Star, Sparkles, Heart, LogOut, CreditCard, Settings,
  MessageCircle, Send, CloudOff, ChevronDown, Gamepad2, Waves, Mic, Layers, Bell, Wind,
  Target, ListChecks, Share2, Loader2,
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { useAuth } from '../../context/AuthContext'
import { Avatar, Card, StatCard, Sidebar, ChildSwitcher, AboutModal, Badge, PlayerCodeChip } from '../../components/ui'
import { useNavigate, Link } from 'react-router-dom'
import { parentAPI, getErrorMessage } from '../../api/client'
import { generateWeeklyRecapCard, shareOrDownloadRecapCard } from '../../lib/weeklyRecapCard'
import toast from 'react-hot-toast'

function formatDate(iso) {
  if (!iso) return 'Not yet played'
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

// Wraps a single category-row Card so parents can click into full history --
// per-attempt log + a trend chart -- lazily fetched from GET
// /parent/history/{category}/{item} the first time a row is expanded, not
// upfront, since most rows are never opened in a given visit.
function ExpandableRow({ category, item, children }) {
  const [open, setOpen] = useState(false)
  const [history, setHistory] = useState(null)
  const [loadingHistory, setLoadingHistory] = useState(false)

  const toggle = () => {
    setOpen(o => !o)
    if (!history && !loadingHistory) {
      setLoadingHistory(true)
      parentAPI.history(category, item.category_name)
        .then(({ data }) => setHistory(data))
        .catch(() => setHistory({ entries: [] }))
        .finally(() => setLoadingHistory(false))
    }
  }

  return (
    <Card
      className="py-4 cursor-pointer hover:bg-white/[0.03] transition-colors"
      onClick={toggle}
    >
      <div className="flex items-center justify-between gap-4">
        {children}
        <ChevronDown
          size={16}
          className={`text-paper/25 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </div>
      {open && (
        <div className="mt-4 pt-4 border-t border-white/[0.06]" onClick={e => e.stopPropagation()}>
          {loadingHistory && <p className="text-paper/30 text-xs">Loading history…</p>}
          {!loadingHistory && history?.entries?.length > 0 && (
            <>
              <div className="h-28 mb-3 -ml-2">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={history.entries.map(e => ({ date: formatDate(e.date), value: e.value }))}>
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }} width={28} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ background: '#12181f', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }} labelStyle={{ color: 'rgba(255,255,255,0.6)' }} />
                    <Line type="monotone" dataKey="value" stroke="#2FB8A6" strokeWidth={2} dot={{ r: 3, fill: '#2FB8A6' }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto">
                {[...history.entries].reverse().map((e, i) => (
                  <div key={i} className="flex items-center justify-between gap-3 text-xs">
                    <span className="text-paper/40 shrink-0">{formatDate(e.date)}</span>
                    <span className="text-paper/70 text-right">{e.label}</span>
                  </div>
                ))}
              </div>
            </>
          )}
          {!loadingHistory && history?.entries?.length === 0 && (
            <p className="text-paper/30 text-xs">No detailed history yet.</p>
          )}
        </div>
      )}
    </Card>
  )
}

// Small expandable stat cell for the weekly-summary grid -- same
// lazy-fetch-on-first-click idea as ExpandableRow above, but sized for a
// single number+label pair instead of a full category card, and reading
// from GET /parent/weekly-breakdown/chime (a per-sound split for just this
// week) rather than the all-time per-item history endpoint.
function ChimeWeeklyStat({ value }) {
  const [open, setOpen] = useState(false)
  const [breakdown, setBreakdown] = useState(null)
  const [loading, setLoading] = useState(false)

  const toggle = (e) => {
    e.stopPropagation()
    setOpen(o => !o)
    if (!breakdown && !loading) {
      setLoading(true)
      parentAPI.chimeWeeklyBreakdown()
        .then(({ data }) => setBreakdown(data))
        .catch(() => setBreakdown({ items: [] }))
        .finally(() => setLoading(false))
    }
  }

  return (
    <div className="col-span-2 sm:col-span-4 -mx-1 px-1" onClick={toggle} role="button" tabIndex={0}>
      <div className="flex items-center gap-1.5 cursor-pointer">
        <div>
          <p className="font-display text-xl font-bold text-paper leading-none tracking-tight">{value}</p>
          <p className="text-paper/40 text-[11px] leading-tight mt-1.5">Chime attempts</p>
        </div>
        <ChevronDown size={13} className={`text-paper/25 mt-1 transition-transform ${open ? 'rotate-180' : ''}`} />
      </div>
      {open && (
        <div className="mt-3 pt-3 border-t border-white/[0.06]" onClick={e => e.stopPropagation()}>
          {loading && <p className="text-paper/30 text-xs">Loading…</p>}
          {!loading && breakdown?.items?.length > 0 && (
            <div className="flex flex-col gap-1.5">
              {breakdown.items.map((it, i) => (
                <div key={i} className="flex items-center justify-between gap-3 text-xs">
                  <span className="text-paper/70">/{it.sound_id}/</span>
                  <span className="text-paper/40">{it.attempts} attempt{it.attempts === 1 ? '' : 's'} · {it.valid_attempts} valid</span>
                </div>
              ))}
            </div>
          )}
          {!loading && breakdown?.items?.length === 0 && (
            <p className="text-paper/30 text-xs">No Chime attempts this week.</p>
          )}
        </div>
      )}
    </div>
  )
}

// The five game sections at the bottom of this page were four near-identical
// hand-written blocks differing only in heading, key, row label formatting
// and whether the right-hand side showed stars or a pass-rate -- ~160 lines
// of copy-paste that drifted apart every time one of them was touched (the
// star markup alone existed twice, verbatim). One config + one component
// instead, so a fix to a row shape lands everywhere at once.
const GAME_SECTIONS = [
  {
    key: 'breathquest', label: 'BreathQuest', icon: Gamepad2, accent: '#FAC775',
    metric: 'stars',
    // BreathQuest always renders its six fixed levels server-side, so this
    // one never actually hits the empty state -- kept for symmetry.
    empty: "Hasn't tried BreathQuest yet.",
  },
  {
    key: 'voicehurdlerace', label: 'Voice Hurdle Race', icon: Waves, accent: '#FAC775',
    metric: 'stars', empty: "Hasn't tried Voice Hurdle Race yet.",
  },
  {
    key: 'vaakmirror', label: 'VaakMirror', icon: Mic, accent: '#2FB8A6',
    metric: 'accuracy', formatName: titleiseSnake, empty: "Hasn't tried VaakMirror yet.",
  },
  {
    key: 'flashcards', label: 'Flashcards', icon: Layers, accent: '#2FB8A6',
    metric: 'accuracy', formatName: (n) => `/${n}/`, empty: "Hasn't tried Flashcards yet.",
  },
  {
    key: 'chime', label: 'Chime', icon: Bell, accent: '#2FB8A6',
    metric: 'accuracy', formatName: (n) => `/${n}/`, empty: "Hasn't tried Chime yet.",
  },
]

function titleiseSnake(name) {
  return String(name).split('_').map(w => w ? w[0].toUpperCase() + w.slice(1) : w).join(' ')
}

// Goal/assignment target_metric values are internal keys (breath_consistency,
// avg_breath_strength) meant for the therapist's Care tab dropdowns -- a
// parent seeing "breath_consistency: 68%" reads as a lab result, not
// something to be proud of. A small friendly-name map, falling back to the
// same titleiseSnake treatment for anything not covered here.
const FRIENDLY_METRIC_NAMES = {
  breath_consistency: 'Steady Breathing',
  avg_breath_strength: 'Breath Strength',
}
function friendlyMetricName(metric) {
  return FRIENDLY_METRIC_NAMES[metric] || titleiseSnake(metric)
}

function Stars({ count = 0 }) {
  return (
    <div className="flex items-center gap-0.5 shrink-0">
      {Array.from({ length: 3 }, (_, j) => (
        <Star
          key={j}
          size={15}
          className="transition-colors"
          style={{ color: j < count ? '#FAC775' : 'rgba(255,255,255,0.12)' }}
          fill={j < count ? '#FAC775' : 'transparent'}
        />
      ))}
    </div>
  )
}

function Accuracy({ pct, trend }) {
  return (
    <div className="flex items-center gap-2 shrink-0">
      {trend === 'up' && <TrendingUp size={14} style={{ color: '#7CDB8A' }} />}
      {trend === 'down' && <TrendingDown size={14} style={{ color: '#FF8F8F' }} />}
      <span className="font-display text-base font-bold text-paper tabular-nums">{pct}%</span>
    </div>
  )
}

function GameSection({ section, items }) {
  const { label, icon: Icon, accent, metric, formatName, empty } = section
  const rows = items ?? []

  return (
    <section className="mb-7">
      <div className="flex items-center gap-2.5 mb-3">
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
          style={{ backgroundColor: `${accent}1f`, border: `1px solid ${accent}33` }}
        >
          <Icon size={14} style={{ color: accent }} />
        </div>
        <h2 className="font-display text-base font-bold text-paper">{label}</h2>
        {rows.length > 0 && (
          <span className="text-paper/25 text-xs tabular-nums">
            {rows.length} {rows.length === 1 ? 'area' : 'areas'}
          </span>
        )}
      </div>

      {rows.length === 0 ? (
        <Card className="py-4 border-dashed border-white/[0.07]">
          <p className="text-paper/35 text-sm">{empty}</p>
        </Card>
      ) : (
        <div className="flex flex-col gap-2">
          {rows.map((cat, i) => (
            <ExpandableRow key={i} category={section.key} item={cat}>
              <div className="min-w-0">
                <p className="text-paper text-sm font-semibold truncate">
                  {formatName ? formatName(cat.category_name) : cat.category_name}
                </p>
                <p className="text-paper/35 text-xs mt-0.5">
                  {cat.attempts} attempt{cat.attempts === 1 ? '' : 's'} · last played {formatDate(cat.last_played)}
                </p>
              </div>
              {metric === 'stars'
                ? <Stars count={cat.stars ?? 0} />
                : <Accuracy pct={cat.accuracy_pct} trend={cat.trend} />}
            </ExpandableRow>
          ))}
        </div>
      )}
    </section>
  )
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
  const [sharingRecap, setSharingRecap] = useState(false)
  const [activity, setActivity] = useState(null)
  const [messages, setMessages] = useState([])
  const [messagesLoaded, setMessagesLoaded] = useState(false)
  const [newMessage, setNewMessage] = useState('')
  const [sendingMessage, setSendingMessage] = useState(false)

  // Extracted so the error state's "Try again" button can re-fire the same
  // fetch, not just the effect on mount.
  const loadProgress = (cancelledRef) =>
    parentAPI.progress()
      .then(({ data }) => { if (!cancelledRef?.current) { setData(data); setStatus('ready') } })
      .catch(() => { if (!cancelledRef?.current) setStatus('error') })

  useEffect(() => {
    const cancelledRef = { current: false }
    setStatus('loading')
    loadProgress(cancelledRef)
    parentAPI.guidedActivity()
      .then(({ data }) => { if (!cancelledRef.current) setActivity(data) })
      .catch(err => console.error('Failed to load guided activity:', err))
    parentAPI.listMessages()
      .then(({ data }) => {
        if (cancelledRef.current) return
        setMessages(data)
        setMessagesLoaded(true)
        // Mark any unread therapist messages as read now that the parent's
        // actually looking at them -- same "seen it" signal the therapist
        // side gets when a parent reads theirs.
        data.filter(m => m.sender_role === 'therapist' && !m.read_at)
          .forEach(m => parentAPI.markMessageRead(m.id).catch(() => {}))
      })
      .catch(err => console.error('Failed to load messages:', err))
    return () => { cancelledRef.current = true }
    // Re-runs when the active child changes (multi-child switcher) -- every
    // one of these endpoints is scoped server-side to parent.patient_id, so
    // switching child without refetching would keep showing the previous
    // child's progress/activity/messages under the new child's name.
  }, [parent?.patient_id])

  const sendMessage = async () => {
    const body = newMessage.trim()
    if (!body) return
    setSendingMessage(true)
    try {
      const { data: sent } = await parentAPI.sendMessage(body)
      setMessages(m => [...m, sent])
      setNewMessage('')
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't send — try again"))
    } finally {
      setSendingMessage(false)
    }
  }

  const starPct = data ? Math.min(100, Math.round((data.total_stars / Math.max(1, data.max_possible_stars)) * 100)) : 0
  const trend = data?.improvement_trend

  const handleShareRecap = async () => {
    if (!data || sharingRecap) return
    setSharingRecap(true)
    try {
      const blob = await generateWeeklyRecapCard(data)
      const filename = `${(data.child_first_name || 'weekly').toLowerCase()}-week-recap.png`
      const result = await shareOrDownloadRecapCard(blob, filename)
      if (result === 'downloaded') toast.success('Saved — ready to share!')
    } catch {
      toast.error("Couldn't create the recap image — try again")
    } finally {
      setSharingRecap(false)
    }
  }

  return (
    <div className="min-h-dvh bg-ink relative flex">
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
          { label: 'Settings', icon: Settings, to: '/parent/settings' },
        ]}
        name={(data?.child_first_name || parent?.child_first_name) ? `${data?.child_first_name || parent?.child_first_name}'s Progress` : undefined}
        onLogout={logout}
        extraFooter={<><ChildSwitcher /><AboutModal role="parent" /></>}
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
          <div className="text-center py-16 flex flex-col items-center">
            <div className="w-14 h-14 rounded-full bg-coral/15 flex items-center justify-center mb-5">
              <CloudOff className="w-6 h-6 text-coral" />
            </div>
            <p className="text-paper/70 font-medium mb-1">Couldn't load progress</p>
            <p className="text-paper/40 text-sm mb-6">Check your connection and give it another try.</p>
            <button
              onClick={() => loadProgress()}
              className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-paper text-sm font-medium transition"
            >
              Try again
            </button>
          </div>
        )}

        {status === 'ready' && data && (
          <>
            {/* Page header. This page used to open cold on a recommendation
                or stats card with no title of its own -- the only thing
                naming the child was the sidebar, which collapses. */}
            <header className="flex items-center gap-4 mb-8">
              <Avatar avatar={data.avatar} size="lg" />
              <div className="min-w-0 flex-1">
                <h1 className="font-display text-2xl font-bold text-paper tracking-tight truncate">
                  {data.child_first_name}'s progress
                </h1>
                <p className="text-paper/40 text-sm mt-0.5">
                  {data.total_sessions > 0
                    ? `${data.total_sessions} session${data.total_sessions === 1 ? '' : 's'} so far · ${data.weekly_summary.stats.home_practice_days}/7 practice days this week`
                    : 'No sessions yet — their first one will show up here.'}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <PlayerCodeChip code={data.player_code} />
                <Link
                  to="/parent/settings"
                  className="w-9 h-9 rounded-full flex items-center justify-center text-paper/40
                             hover:text-paper hover:bg-white/[0.06] transition-colors"
                  title="Settings"
                >
                  <Settings size={16} />
                </Link>
              </div>
            </header>

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
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleShareRecap}
                    disabled={sharingRecap}
                    className="flex items-center gap-1.5 text-xs font-semibold text-mint hover:text-mint-light
                               disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {sharingRecap ? <Loader2 size={13} className="animate-spin" /> : <Share2 size={13} />}
                    Share
                  </button>
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
              </div>
              {/* Grouped, not a nine-cell wall of bare numbers. The old grid
                  ran every stat together at equal weight with cryptic labels
                  ("— completed" under "BreathQuest"), so a parent had to
                  decode which number belonged to what. Three labelled groups
                  with the practice figures given the most weight, since
                  that's the one a parent can actually act on. */}
              <div className="flex flex-col gap-4 mb-5">
                <div className="flex items-end gap-5">
                  <div>
                    <p className="font-display text-3xl font-bold text-paper leading-none tracking-tight tabular-nums">
                      {data.weekly_summary.stats.home_practice_days}
                      <span className="text-paper/25 text-xl">/7</span>
                    </p>
                    <p className="text-paper/40 text-[11px] leading-tight mt-2">days practised at home</p>
                  </div>
                  <div className="pb-0.5">
                    <p className="font-display text-xl font-bold text-paper leading-none tracking-tight tabular-nums">
                      {data.weekly_summary.stats.home_practice_minutes}
                    </p>
                    <p className="text-paper/40 text-[11px] leading-tight mt-1.5">minutes logged</p>
                  </div>
                </div>

                {/* Weekly practice strip -- a bar per day rather than a bare
                    count, so "3 days" reads as a shape at a glance. */}
                <div className="flex gap-1">
                  {Array.from({ length: 7 }, (_, i) => (
                    <div
                      key={i}
                      className={`h-1.5 flex-1 rounded-full transition-colors ${
                        i < (data.weekly_summary.stats.home_practice_days ?? 0)
                          ? 'bg-mint'
                          : 'bg-white/[0.08]'
                      }`}
                    />
                  ))}
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-4 pt-1 border-t border-white/[0.06]">
                  {[
                    ['BreathQuest sessions', data.weekly_summary.stats.bq_sessions],
                    ['of those, completed', data.weekly_summary.stats.bq_completed],
                    ['Assignments done', data.weekly_summary.stats.assignments_completed],
                    ['Assignments overdue', data.weekly_summary.stats.assignments_overdue, 'warn'],
                    ['Goals open', data.weekly_summary.stats.goals_open],
                    ['Goals achieved', data.weekly_summary.stats.goals_achieved_total],
                  ].map(([label, value, tone], i) => (
                    <div key={i}>
                      <p className={`font-display text-xl font-bold leading-none tracking-tight tabular-nums ${
                        tone === 'warn' && value > 0 ? 'text-coral-light' : 'text-paper'
                      }`}>
                        {value}
                      </p>
                      <p className="text-paper/40 text-[11px] leading-tight mt-1.5">{label}</p>
                    </div>
                  ))}
                  <ChimeWeeklyStat value={data.weekly_summary.stats.chime_attempts} />
                </div>
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

            {/* Stars + breath consistency together. These were two separate
                full-width cards, the second of which was a single label and a
                single percentage on its own line -- a whole card's worth of
                chrome for one number. */}
            <Card className="mb-8">
              <div className="flex items-center justify-between mb-3">
                <span className="text-paper/60 text-sm font-medium">Total stars</span>
                <span className="text-paper/40 text-xs tabular-nums">{data.total_stars} / {data.max_possible_stars}</span>
              </div>
              <div className="h-3 rounded-full bg-white/[0.06] overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-brand-amber to-ember rounded-full transition-[width] duration-700"
                  style={{ width: `${starPct}%` }}
                />
              </div>

              {data.avg_breath_consistency != null && (
                <div className="flex items-center justify-between mt-5 pt-4 border-t border-white/[0.06]">
                  <span className="flex items-center gap-2 text-paper/60 text-sm font-medium">
                    <Wind size={15} className="text-mint" />
                    Breath consistency
                  </span>
                  <span className="font-display text-base font-bold text-mint-light tabular-nums">
                    {Math.round(data.avg_breath_consistency * 100)}%
                  </span>
                </div>
              )}
            </Card>

            {/* Goals + Assignments -- the weekly summary above only ever
                showed counts ("2 goals open"), never what those goals or
                assignments actually are. Only rendered once there's
                something to show; an empty state here would just be
                another card saying "nothing yet" next to a therapist
                connection prompt that already covers that case below. */}
            {data.goals?.length > 0 && (
              <Card className="mb-8">
                <div className="flex items-center gap-2 mb-4">
                  <Target size={16} className="text-mint" />
                  <span className="text-paper/60 text-sm font-medium">Goals</span>
                </div>
                <div className="flex flex-col gap-3">
                  {data.goals.map(g => {
                    const pct = g.current_value != null
                      ? Math.min(100, Math.round((g.current_value / g.target_value) * 100))
                      : null
                    return (
                      <div key={g.id}>
                        <div className="flex items-center justify-between gap-3 mb-1.5">
                          <span className="text-paper text-sm font-semibold">{friendlyMetricName(g.target_metric)}</span>
                          <Badge color={g.achieved ? 'green' : 'gray'}>{g.achieved ? 'Achieved' : 'In progress'}</Badge>
                        </div>
                        {pct != null ? (
                          <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-mint to-brand-green rounded-full transition-[width] duration-700"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        ) : (
                          <p className="text-paper/30 text-xs">Not enough recent sessions yet to show progress.</p>
                        )}
                      </div>
                    )
                  })}
                </div>
              </Card>
            )}

            {data.assignments?.length > 0 && (
              <Card className="mb-8">
                <div className="flex items-center gap-2 mb-4">
                  <ListChecks size={16} className="text-coral-light" />
                  <span className="text-paper/60 text-sm font-medium">Assignments</span>
                </div>
                <div className="flex flex-col gap-2">
                  {data.assignments.map(a => (
                    <div key={a.id} className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-paper text-sm font-semibold truncate">{a.title}</p>
                        {a.due_at && (
                          <p className="text-paper/35 text-xs mt-0.5">Due {formatDate(a.due_at)}</p>
                        )}
                      </div>
                      <Badge color={a.status === 'completed' ? 'green' : a.status === 'overdue' ? 'coral' : 'gray'}>
                        {titleiseSnake(a.status)}
                      </Badge>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Messages -- parent's side of the same therapist<->parent
                log the therapist writes to from PatientDetail.jsx's Care
                tab. Only shown once a therapist is actually linked --
                messaging with no therapist on the other end would silently
                vanish into nothing, which is worse than not offering it. */}
            {data?.has_therapist ? (
            <Card className="mb-8">
              <div className="flex items-center gap-2 mb-3">
                <MessageCircle className="w-4 h-4 text-paper/40" />
                <span className="text-paper/60 text-sm font-medium">Messages with your therapist</span>
              </div>
              <div className="flex flex-col gap-2 mb-3 max-h-64 overflow-y-auto">
                {messagesLoaded && messages.length === 0 && (
                  <p className="text-paper/30 text-sm">No messages yet — say hi!</p>
                )}
                {messages.map(m => {
                  const mine = m.sender_role === 'parent'
                  return (
                    <div key={m.id} className={`flex flex-col max-w-[85%] ${mine ? 'self-end items-end' : 'items-start'}`}>
                      <div className={`text-sm leading-relaxed px-3.5 py-2.5 ${
                        mine
                          ? 'bg-coral/20 text-paper rounded-2xl rounded-br-md'
                          : 'bg-white/[0.06] text-paper rounded-2xl rounded-bl-md'
                      }`}>
                        {m.body}
                      </div>
                      <p className="text-paper/25 text-[10px] mt-1 px-1">
                        {mine ? 'You' : "Your child's therapist"} · {new Date(m.created_at).toLocaleString(undefined, {
                          month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
                        })}
                      </p>
                    </div>
                  )
                })}
              </div>
              <div className="flex gap-2">
                <input
                  className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-paper
                             placeholder:text-paper/30 focus:outline-none focus:border-coral/40"
                  placeholder="Message your therapist…"
                  value={newMessage}
                  onChange={e => setNewMessage(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && sendMessage()}
                />
                <button
                  onClick={sendMessage}
                  disabled={sendingMessage || !newMessage.trim()}
                  className="px-4 py-2 rounded-xl bg-coral hover:bg-coral/90 text-paper text-sm font-semibold
                             disabled:opacity-40 transition-colors flex items-center gap-1.5"
                >
                  <Send className="w-3.5 h-3.5" /> Send
                </button>
              </div>
            </Card>
            ) : (
              <Card className="mb-8">
                <div className="flex items-center gap-2 mb-2">
                  <MessageCircle className="w-4 h-4 text-paper/40" />
                  <span className="text-paper/60 text-sm font-medium">Messages with your therapist</span>
                </div>
                <p className="text-paper/40 text-sm leading-relaxed">
                  Your child isn't connected with a therapist yet, so there's no one to message here.
                  Once they're linked with a therapist, you'll be able to chat with them right from this page.
                </p>
              </Card>
            )}

            {/* One <GameSection> per game (see GAME_SECTIONS above) instead
                of four hand-copied blocks. Sections always render, even with
                no sessions -- a game vanishing entirely made the app look
                BreathQuest-only rather than "not tried yet". */}
            {GAME_SECTIONS.map(section => (
              <GameSection key={section.key} section={section} items={data.categories?.[section.key]} />
            ))}

          </>
        )}
      </div>
    </div>
  )
}
