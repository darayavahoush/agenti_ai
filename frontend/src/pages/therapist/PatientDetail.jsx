import { useState, useEffect, useCallback } from 'react'
import toast from 'react-hot-toast'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { dashboardAPI, chimeAPI, vaakmirrorAPI, getErrorMessage } from '../../api/client'
import { voiceHurdleRaceApi } from '../../api/voiceHurdleRaceApi'
import { Card, Badge, Avatar, StarRating, Button, Spinner, PageLoader, Sidebar, AmbientGlow, ProgressRing, AboutModal, LevelIcon, PlayerCodeChip } from '../../components/ui'
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
         BarChart, Bar, XAxis, YAxis, Tooltip, LineChart, Line, Legend } from 'recharts'
import { Download, BarChart3, Gamepad2, Dog, Bell, Waves, HeartPulse, FileText, LayoutDashboard, X, Check, ChevronLeft, ChevronRight, Brain, ClipboardCheck, Play, Lightbulb, Settings, Target, ListChecks, MessageSquare, Activity, CloudOff, ChevronDown, Wind, Clock } from 'lucide-react'

// Labeling Queue badge colors, keyed by the only three tiers MirrorMirror.jsx's
// scoreAgainstTarget ever assigns to an attempt (see mouthMetrics.js) --
// green/yellow/red mapped onto Badge's own green/amber/coral palette.
const TIER_COLORS = { green: 'green', yellow: 'amber', red: 'coral' }

// Level Details rows expand in place to show that level's own session
// history -- filtered client-side from `sessions` (data.recent_sessions),
// which the Sessions tab already has in full, so no extra fetch is needed
// just to drill into one level.
function ExpandableLevelRow({ level, sessions, children }) {
  const [open, setOpen] = useState(false)
  const levelSessions = sessions.filter(s => s.level_id === level.level_id)
    .slice().sort((a, b) => new Date(a.started_at) - new Date(b.started_at))
  const chartData = levelSessions.map(s => ({
    date: new Date(s.started_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    stars: s.stars_earned || 0,
  }))

  return (
    <div className="rounded-xl border border-white/5">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 px-1 py-1 text-left hover:bg-white/[0.03] rounded-xl transition-colors"
      >
        {children}
        <ChevronDown size={14} className={`text-white/25 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="px-3 pb-3 pt-1">
          {levelSessions.length === 0 ? (
            <p className="text-white/30 text-xs py-2">No sessions logged for this level yet.</p>
          ) : (
            <>
              <div className="h-24 mb-2 -ml-2">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.3)' }} axisLine={false} tickLine={false} />
                    <YAxis domain={[0, 3]} ticks={[0, 1, 2, 3]} tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.3)' }} width={20} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ background: '#1E1E3F', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }} labelStyle={{ color: 'rgba(255,255,255,0.5)' }} />
                    <Line type="monotone" dataKey="stars" stroke="#A8FF6F" strokeWidth={2} dot={{ r: 3, fill: '#A8FF6F' }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-col gap-1 max-h-32 overflow-y-auto">
                {levelSessions.slice().reverse().map(s => (
                  <div key={s.id} className="flex items-center justify-between text-xs">
                    <span className="text-white/40">{new Date(s.started_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
                    <span className="text-white/70">{s.stars_earned || 0}★ {s.completed ? '' : '· not completed'}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

// Same visual pattern as ExpandableLevelRow above, but for a Goal: data
// isn't in-memory sessions already loaded for the page, so this lazily
// fetches GET /dashboard/goals/{id}/history (a raw per-session series
// behind the goal's rolling-average current_value) on first expand rather
// than eagerly loading history for every goal up front.
function ExpandableGoalRow({ goal, children }) {
  const [open, setOpen] = useState(false)
  const [history, setHistory] = useState(null)
  const [loading, setLoading] = useState(false)

  const toggle = () => {
    setOpen(o => !o)
    if (!history && !loading) {
      setLoading(true)
      dashboardAPI.goalHistory(goal.id)
        .then(({ data }) => setHistory(data))
        .catch(() => setHistory([]))
        .finally(() => setLoading(false))
    }
  }

  const chartData = (history || []).map(e => ({
    date: new Date(e.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    value: e.value,
  }))

  return (
    <div className="rounded-xl border border-white/5">
      <div
        onClick={toggle}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggle() }}
        className="w-full flex items-center gap-3 px-1 py-1 text-left hover:bg-white/[0.03] rounded-xl transition-colors cursor-pointer"
      >
        {children}
        <ChevronDown size={14} className={`text-white/25 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </div>
      {open && (
        <div className="px-3 pb-3 pt-1">
          {loading && <p className="text-white/30 text-xs py-2">Loading…</p>}
          {!loading && history?.length === 0 && (
            <p className="text-white/30 text-xs py-2">No BreathQuest sessions with this metric yet.</p>
          )}
          {!loading && history?.length > 0 && (
            <>
              <div className="h-24 mb-2 -ml-2">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.3)' }} axisLine={false} tickLine={false} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.3)' }} width={24} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ background: '#1E1E3F', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }} labelStyle={{ color: 'rgba(255,255,255,0.5)' }} />
                    <Line type="monotone" dataKey="value" stroke="#5BC8F5" strokeWidth={2} dot={{ r: 3, fill: '#5BC8F5' }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-col gap-1 max-h-32 overflow-y-auto">
                {[...history].reverse().map((e, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <span className="text-white/40">{new Date(e.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
                    <span className="text-white/70">{e.label}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

// Same lazy-fetch-on-expand pattern as ExpandableGoalRow, but for an
// Assignment: shows sessions/attempts in the assigned game+level that fall
// within the assignment's active window. There's no stored link from an
// Assignment to a specific session (completion is a manual status flip),
// so this is a best-match list for the therapist to eyeball -- not a
// definitive "this session fulfilled it" answer, and the panel says so.
function ExpandableAssignmentRow({ assignment, children }) {
  const [open, setOpen] = useState(false)
  const [sessions, setSessions] = useState(null)
  const [loading, setLoading] = useState(false)

  const toggle = () => {
    setOpen(o => !o)
    if (!sessions && !loading) {
      setLoading(true)
      dashboardAPI.matchingSessions(assignment.id)
        .then(({ data }) => setSessions(data))
        .catch(() => setSessions([]))
        .finally(() => setLoading(false))
    }
  }

  const chartData = (sessions || []).map(e => ({
    date: new Date(e.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    value: e.value,
  }))

  return (
    <div className="rounded-xl border border-white/5">
      <div
        onClick={toggle}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggle() }}
        className="w-full flex items-center gap-3 px-1 py-1 text-left hover:bg-white/[0.03] rounded-xl transition-colors cursor-pointer"
      >
        {children}
        <ChevronDown size={14} className={`text-white/25 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </div>
      {open && (
        <div className="px-3 pb-3 pt-1">
          {loading && <p className="text-white/30 text-xs py-2">Loading…</p>}
          {!loading && sessions?.length === 0 && (
            <p className="text-white/30 text-xs py-2">No matching sessions found in this assignment's active window.</p>
          )}
          {!loading && sessions?.length > 0 && (
            <>
              <p className="text-white/25 text-[10px] mb-2">
                Best-match sessions in this game/level during the assignment window -- not a confirmed link.
              </p>
              <div className="h-24 mb-2 -ml-2">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.3)' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.3)' }} width={24} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ background: '#1E1E3F', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }} labelStyle={{ color: 'rgba(255,255,255,0.5)' }} />
                    <Line type="monotone" dataKey="value" stroke="#5BC8F5" strokeWidth={2} dot={{ r: 3, fill: '#5BC8F5' }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-col gap-1 max-h-32 overflow-y-auto">
                {[...sessions].reverse().map((e, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <span className="text-white/40">{new Date(e.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
                    <span className="text-white/70">{e.label}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

// Small pill for a phoneme in the Flashcards tab's strongest/weakest rows --
// tone picks the accent color, trend shows the same up/down/flat arrow
// convention as the Sound Accuracy strip elsewhere on this page.
function PhonemePill({ p, tone }) {
  const toneClasses = tone === 'green'
    ? 'border-brand-green/30 bg-brand-green/5 text-brand-green'
    : 'border-brand-coral/30 bg-brand-coral/5 text-brand-coral'
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm ${toneClasses}`}>
      <span className="font-mono uppercase font-semibold">{p.phoneme}</span>
      <span className="text-white/50">{p.accuracy}%</span>
      {p.trend && (
        <span className={p.trend === 'up' ? 'text-brand-green' : p.trend === 'down' ? 'text-brand-coral' : 'text-white/30'}>
          {p.trend === 'up' ? '↑' : p.trend === 'down' ? '↓' : '→'}
        </span>
      )}
    </div>
  )
}

// Cross-game phoneme summary (GET /dashboard/patients/{id}/phoneme-summary)
// -- the one place accuracy is pooled across Flashcards + VaakMirror + Chime
// per phoneme, instead of three separate per-game views. See backend
// services/phoneme_crosswalk.py + phoneme_summary.py for how each game's
// own sound/level ids get reconciled onto one vocabulary.
const CATEGORY_LABELS = {
  stop: 'Stops', fricative: 'Fricatives', affricate: 'Affricates',
  nasal: 'Nasals', liquid: 'Liquids', glide: 'Glides', vowel: 'Vowels',
  other: 'Other',
}
const GAME_LABELS = { flashcards: 'Flashcards', vaakmirror: 'VaakMirror', chime: 'Chime' }
const GAME_DOT_COLOR = { flashcards: '#A8FF6F', vaakmirror: '#5FD4E0', chime: '#FFB86B' }

function accuracyTone(accuracy) {
  if (accuracy >= 0.8) return 'green'
  if (accuracy >= 0.5) return 'amber'
  return 'coral'
}
const TONE_TEXT = { green: 'text-brand-green', amber: 'text-brand-amber', coral: 'text-brand-coral' }
const TONE_BORDER = { green: 'border-brand-green/30 bg-brand-green/5', amber: 'border-brand-amber/30 bg-brand-amber/5', coral: 'border-brand-coral/30 bg-brand-coral/5' }
const TONE_BAR = { green: '#A8FF6F', amber: '#FFC857', coral: '#FF6B6B' }

// One phoneme chip in the full grid -- small always-visible per-game dots
// give an at-a-glance read of which games contributed even when collapsed;
// expanding still shows the full per-game accuracy breakdown.
function PhonemeChip({ p }) {
  const [open, setOpen] = useState(false)
  const tone = accuracyTone(p.accuracy)
  return (
    <div className={`rounded-xl border text-sm transition-colors ${TONE_BORDER[tone]}`}>
      <button onClick={() => setOpen(o => !o)} className="w-full flex items-center gap-2 px-3 py-2 text-left">
        <span className="font-mono uppercase font-semibold text-white">{p.phoneme}</span>
        {p.example_word && <span className="text-white/30 text-xs italic hidden sm:inline">"{p.example_word}"</span>}
        <span className="flex-1" />
        <span className="flex items-center gap-1" title={p.by_game.map(g => `${GAME_LABELS[g.game] || g.game}: ${Math.round(g.accuracy * 100)}% (${g.attempts}×)`).join(' · ')}>
          {p.by_game.map(g => (
            <span key={g.game} className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: GAME_DOT_COLOR[g.game] || '#888' }} />
          ))}
        </span>
        <span className={`font-semibold ${TONE_TEXT[tone]}`}>{Math.round(p.accuracy * 100)}%</span>
        <span className="text-white/30 text-xs">{p.attempts}×</span>
        <ChevronDown size={12} className={`text-white/25 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="px-3 pb-2.5 pt-0.5 flex flex-col gap-1">
          {p.by_game.map(g => (
            <div key={g.game} className="flex items-center gap-2 text-xs">
              <span className="w-2 h-2 rounded-full shrink-0" style={{ background: GAME_DOT_COLOR[g.game] || '#888' }} />
              <span className="text-white/50 w-20 shrink-0">{GAME_LABELS[g.game] || g.game}</span>
              <div className="flex-1 h-1 bg-white/10 rounded-full overflow-hidden">
                <div className="h-full rounded-full" style={{ width: `${Math.round(g.accuracy * 100)}%`, background: TONE_BAR[accuracyTone(g.accuracy)] }} />
              </div>
              <span className="text-white/40 w-16 text-right">{g.correct}/{g.attempts}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// At-a-glance strip: one stat block per game, from summary.game_totals --
// what each game contributed overall, independent of which phonemes it
// happened to touch. Lets a therapist see "VaakMirror's numbers look off"
// without expanding a single phoneme chip.
function GameTotalsStrip({ gameTotals }) {
  if (!gameTotals || gameTotals.length === 0) return null
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-5">
      {gameTotals.map(g => {
        const tone = accuracyTone(g.accuracy)
        return (
          <div key={g.game} className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: GAME_DOT_COLOR[g.game] || '#888' }} />
            <div className="flex-1 min-w-0">
              <div className="text-white/50 text-xs truncate">{GAME_LABELS[g.game] || g.game}</div>
              <div className="text-white/30 text-[11px]">{g.attempts} attempts</div>
            </div>
            <span className={`text-base font-bold ${TONE_TEXT[tone]}`}>{Math.round(g.accuracy * 100)}%</span>
          </div>
        )
      })}
    </div>
  )
}

function PhonemeSummaryCard({ summary, loading, error }) {
  if (loading) {
    return (
      <Card className="md:col-span-2 flex items-center justify-center py-12">
        <Spinner />
      </Card>
    )
  }
  if (error || !summary) {
    return (
      <Card className="md:col-span-2">
        <div className="flex items-center gap-2 text-white/40 text-sm py-6 justify-center">
          <CloudOff size={16} />
          Couldn't load the cross-game phoneme summary.
        </div>
      </Card>
    )
  }
  if (summary.total_attempts === 0) {
    return (
      <Card className="md:col-span-2">
        <h3 className="font-semibold text-white mb-1 flex items-center gap-2">
          <Brain size={16} className="text-brand-teal" />
          Phoneme Command Center
        </h3>
        <p className="text-white/30 text-xs py-6 text-center">
          No phoneme-level attempts yet across Flashcards, VaakMirror, or Chime.
        </p>
      </Card>
    )
  }

  const overallTone = accuracyTone(summary.overall_accuracy)
  const maxCategoryAttempts = Math.max(...summary.by_category.map(c => c.attempts), 1)

  return (
    <Card className="md:col-span-2 animate-card-pop motion-reduce:!opacity-100 motion-reduce:animate-none"
          style={{ opacity: 0, animationDelay: '0.08s' }}>
      <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
        <h3 className="font-semibold text-white flex items-center gap-2">
          <Brain size={16} className="text-brand-teal" />
          Phoneme Command Center
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-white/30 text-xs">{summary.total_attempts} attempts · every game combined</span>
          <span className={`text-lg font-bold ${TONE_TEXT[overallTone]}`}>{Math.round(summary.overall_accuracy * 100)}%</span>
        </div>
      </div>
      <p className="text-white/30 text-xs mb-5">
        One accuracy number per phoneme, pooled across Flashcards, VaakMirror, and Chime.
      </p>

      {/* At-a-glance: what each game contributed overall */}
      <GameTotalsStrip gameTotals={summary.game_totals} />

      {/* Articulatory category rollup */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 mb-6">
        {summary.by_category.map(c => {
          const tone = accuracyTone(c.accuracy)
          return (
            <div key={c.category} className="flex items-center gap-2 text-xs">
              <span className="text-white/50 w-20 shrink-0">{CATEGORY_LABELS[c.category] || c.category}</span>
              <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all duration-500"
                     style={{ width: `${(c.attempts / maxCategoryAttempts) * 100}%`, background: TONE_BAR[tone], opacity: 0.85 }} />
              </div>
              <span className={`w-10 text-right font-semibold ${TONE_TEXT[tone]}`}>{Math.round(c.accuracy * 100)}%</span>
            </div>
          )
        })}
      </div>

      {/* Priority focus -- weakest phonemes with enough data to trust */}
      {summary.weakest.length > 0 && (
        <div className="mb-5">
          <h4 className="text-white/50 text-xs font-semibold uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Target size={12} />
            Priority Focus
          </h4>
          <div className="flex flex-wrap gap-2">
            {summary.weakest.map(p => (
              <PhonemePill key={p.phoneme} p={{ phoneme: p.phoneme, accuracy: Math.round(p.accuracy * 100) }} tone="coral" />
            ))}
          </div>
        </div>
      )}

      {/* Full phoneme grid, worst-accuracy-first */}
      <div>
        <h4 className="text-white/50 text-xs font-semibold uppercase tracking-wide mb-2">All Phonemes Practiced</h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-96 overflow-y-auto pr-1">
          {summary.phonemes.map(p => <PhonemeChip key={p.phoneme} p={p} />)}
        </div>
      </div>
    </Card>
  )
}

const LEVEL_EMOJIS = {
  pinwheel: '🌀', float_rider: '🐥', candle: '🕯️',
  balloon: '🎈', dandelion: '🌼', dragon: '🐉'
}

const VM_GAMES = ['mirror_mirror', 'tongue_tamer', 'lip_sync_hero']
const VM_GAME_LABELS = {
  mirror_mirror: 'Mirror Mirror', tongue_tamer: 'Tongue Tamer', lip_sync_hero: 'Lip Sync Hero',
}

// recommended_action vocabulary from breathquest_agent/service.py's decide().
const ACTION_STYLE = {
  raise: { label: 'Raise difficulty', color: 'green' },
  hold:  { label: 'Hold steady',      color: 'gray'  },
  lower: { label: 'Lower difficulty', color: 'amber' },
}

// recommendation_policy vocabulary — mirrors AgentService.decide()'s
// Literal[...] exactly, so an unrecognized value here signals the backend
// added a new policy this map hasn't caught up with yet, not a typo.
const POLICY_LABEL = {
  rule_based:    'Rule-based',
  tabular_q:     'Learned (per-child)',
  bandit:        'Bandit (retired)',
  ppo:           'PPO',
  recurrent_ppo: 'Recurrent PPO',
}

// Quick-fill presets for the most common goals a therapist sets, since
// picking a metric + typing a target % + picking a date by hand is the
// most repetitive part of the Care tab. These just prefill newGoal --
// still fully editable before saving, not a locked-in shortcut.
const GOAL_PRESETS = [
  { label: 'Steady Breathing · 75% in 4 wks', target_metric: 'breath_consistency', target_value: '75', weeks: 4 },
  { label: 'Steady Breathing · 90% in 8 wks', target_metric: 'breath_consistency', target_value: '90', weeks: 8 },
  { label: 'Breath Strength · 70% in 4 wks',  target_metric: 'avg_breath_strength', target_value: '70', weeks: 4 },
]

function presetTargetDate(weeks) {
  const d = new Date()
  d.setDate(d.getDate() + weeks * 7)
  return d.toISOString().slice(0, 10)
}

function relativeDate(iso) {
  if (!iso) return 'Never played'
  const days = Math.floor((Date.now() - new Date(iso)) / 86400000)
  if (days <= 0) return 'Today'
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days} days ago`
  return new Date(iso).toLocaleDateString('en', { month: 'short', day: 'numeric' })
}

export default function PatientDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { therapist, logout, startSupervisedSession } = useAuth()
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab]         = useState('progress')   // progress | sessions | voicehurdlerace | chime | vaakmirror | care | notes
  const [downloadingReport, setDownloadingReport] = useState(false)
  const [reportError, setReportError] = useState('')
  const [launchingSession, setLaunchingSession] = useState(null) // null | 'assessment' | 'play'
  const [soundProgress, setSoundProgress] = useState(null)
  const [soundProgressLoading, setSoundProgressLoading] = useState(true)
  // Isolate one sound's line in the "Sound Accuracy Over Time" chart --
  // click a sound (in the stats strip or the chart legend) to dim the rest.
  const [selectedSound, setSelectedSound] = useState(null)
  const [noteText, setNoteText] = useState('')
  const [notes, setNotes]       = useState([])
  const [savingNote, setSavingNote] = useState(false)
  const [vhrSessions, setVhrSessions] = useState([])
  const [vhrLoading, setVhrLoading]   = useState(true)
  const [chimeEvents, setChimeEvents] = useState([])
  const [chimeLoading, setChimeLoading] = useState(true)
  const [chimeError, setChimeError] = useState(false)
  const [vmDashboard, setVmDashboard] = useState(null)
  const [vmLoading, setVmLoading] = useState(true)
  const [vmError, setVmError] = useState(false)
  const [attempts, setAttempts] = useState([])
  const [attemptsLoading, setAttemptsLoading] = useState(true)
  const [labelingId, setLabelingId] = useState(null)
  const [flashcardsData, setFlashcardsData] = useState(null)
  const [flashcardsLoading, setFlashcardsLoading] = useState(true)
  const [flashcardsError, setFlashcardsError] = useState(false)
  const [phonemeSummary, setPhonemeSummary] = useState(null)
  const [phonemeSummaryLoading, setPhonemeSummaryLoading] = useState(true)
  const [phonemeSummaryError, setPhonemeSummaryError] = useState(false)
  const [agentSuggestions, setAgentSuggestions] = useState({})
  const [agentLoading, setAgentLoading] = useState(true)
  const [dismissedSuggestions, setDismissedSuggestions] = useState({})
  const [applyingSuggestion, setApplyingSuggestion] = useState(null)

  // Care tab — Assignments / Goals / Messages / Home Practice / Weekly Summary
  const [assignments, setAssignments] = useState([])
  const [goals, setGoals]             = useState([])
  const [messages, setMessages]       = useState([])
  const [homePractice, setHomePractice] = useState([])
  const [careLoading, setCareLoading] = useState(true)
  const [careError, setCareError]     = useState(false)
  const [weekOffset, setWeekOffset]   = useState(0)
  const [weeklySummary, setWeeklySummary] = useState(null)
  const [summaryLoading, setSummaryLoading] = useState(true)

  const [newAssignment, setNewAssignment] = useState({ game: 'chime', level_id: '', title: '', instructions: '', due_at: '' })
  const [savingAssignment, setSavingAssignment] = useState(false)
  const [ideaCondition, setIdeaCondition] = useState('')
  const [ideas, setIdeas] = useState([])
  const [ideasLoading, setIdeasLoading] = useState(false)
  const [ideasOpen, setIdeasOpen] = useState(false)
  const [newGoal, setNewGoal] = useState({ target_metric: 'breath_consistency', target_value: '', target_date: '' })
  const [savingGoal, setSavingGoal] = useState(false)
  const [newMessage, setNewMessage] = useState('')
  const [sendingMessage, setSendingMessage] = useState(false)
  const [newPractice, setNewPractice] = useState({ practiced_on: new Date().toISOString().slice(0, 10), duration_minutes: '', notes: '' })
  const [savingPractice, setSavingPractice] = useState(false)

  const loadCareData = useCallback(() => {
    setCareLoading(true)
    Promise.all([
      dashboardAPI.listAssignments(id),
      dashboardAPI.listGoals(id),
      dashboardAPI.listMessages(id),
      dashboardAPI.listHomePractice(id),
    ]).then(([a, g, m, h]) => {
      setAssignments(a.data)
      setGoals(g.data)
      setMessages(m.data)
      setHomePractice(h.data)
    }).catch(err => { console.error('Failed to load Care tab data:', err); setCareError(true) })
      .finally(() => setCareLoading(false))
  }, [id])

  useEffect(() => {
    Promise.all([
      dashboardAPI.progress(id),
      dashboardAPI.listNotes(id),
    ]).then(([prog, notesRes]) => {
      setData(prog.data)
      setNotes(notesRes.data)
    }).finally(() => setLoading(false))

    voiceHurdleRaceApi.getVoiceHurdleRaceSessions(id)
      .then(setVhrSessions)
      .catch(err => console.error('Failed to load Voice Hurdle Race sessions:', err))
      .finally(() => setVhrLoading(false))

    chimeAPI.getPatientEvents(id)
      .then(({ data }) => setChimeEvents(data))
      .catch(err => { console.error('Failed to load Chime events:', err); setChimeError(true) })
      .finally(() => setChimeLoading(false))

    vaakmirrorAPI.getPatientDashboard(id)
      .then(({ data }) => setVmDashboard(data))
      .catch(err => { console.error('Failed to load VaakMirror dashboard:', err); setVmError(true) })
      .finally(() => setVmLoading(false))

    vaakmirrorAPI.getPatientAttempts(id, { unlabeled_only: true, limit: 30 })
      .then(({ data }) => setAttempts(data))
      .catch(err => console.error('Failed to load VaakMirror attempts:', err))
      .finally(() => setAttemptsLoading(false))

    dashboardAPI.getFlashcardsProgress(id)
      .then(({ data }) => setFlashcardsData(data))
      .catch(err => { console.error('Failed to load Flashcards progress:', err); setFlashcardsError(true) })
      .finally(() => setFlashcardsLoading(false))

    dashboardAPI.getSoundProgress(id)
      .then(({ data }) => setSoundProgress(data))
      .catch(err => console.error('Failed to load sound progress:', err))
      .finally(() => setSoundProgressLoading(false))

    dashboardAPI.getPhonemeSummary(id)
      .then(({ data }) => setPhonemeSummary(data))
      .catch(err => { console.error('Failed to load phoneme summary:', err); setPhonemeSummaryError(true) })
      .finally(() => setPhonemeSummaryLoading(false))

    // The same adaptive-difficulty agent Chime and BreathQuest use, applied
    // to VaakMirror's round_size knob (see backend vaakmirror/agent_bridge.py).
    // Read-only here — a therapist has to accept a suggestion before it
    // changes anything.
    Promise.all(
      VM_GAMES.map(g =>
        vaakmirrorAPI.getGameSettingsSuggestion(id, g)
          .then(({ data }) => [g, data])
          .catch(() => [g, null])
      )
    ).then(entries => {
      setAgentSuggestions(Object.fromEntries(entries.filter(([, v]) => v)))
    }).finally(() => setAgentLoading(false))

    loadCareData()
  }, [id, loadCareData])

  useEffect(() => {
    setSummaryLoading(true)
    dashboardAPI.weeklySummary(id, weekOffset)
      .then(({ data }) => setWeeklySummary(data))
      .catch(err => console.error('Failed to load weekly summary:', err))
      .finally(() => setSummaryLoading(false))
  }, [id, weekOffset])

  useEffect(() => {
    if (!ideasOpen) return
    setIdeasLoading(true)
    dashboardAPI.listHomePracticeIdeas(ideaCondition || undefined)
      .then(({ data }) => setIdeas(data))
      .catch(err => console.error('Failed to load home practice ideas:', err))
      .finally(() => setIdeasLoading(false))
  }, [ideasOpen, ideaCondition])

  // Accepting a suggestion goes through the normal update endpoint — same
  // as if the therapist had typed the number in themselves — so it's always
  // a human decision on record, never the agent silently changing things.
  const labelAttempt = (attemptId, label) => {
    setLabelingId(attemptId)
    vaakmirrorAPI.labelAttempt(attemptId, label)
      .then(() => setAttempts(prev => prev.filter(a => a.id !== attemptId)))
      .catch(err => console.error('Failed to label attempt:', err))
      .finally(() => setLabelingId(null))
  }

  const acceptAgentSuggestion = (game) => {
    const suggestion = agentSuggestions[game]
    if (!suggestion) return
    setApplyingSuggestion(game)
    vaakmirrorAPI.updateGameSettings(id, game, { round_size: suggestion.suggested_round_size })
      .then(() => {
        setAgentSuggestions(prev => ({
          ...prev,
          [game]: { ...prev[game], current_round_size: suggestion.suggested_round_size, action: 'hold' },
        }))
      })
      .catch(err => console.error('Failed to apply agent suggestion:', err))
      .finally(() => setApplyingSuggestion(null))
  }

  const dismissAgentSuggestion = (game) => {
    setDismissedSuggestions(prev => ({ ...prev, [game]: true }))
  }

  // Launches a supervised session (see AuthContext.jsx's startSupervisedSession)
  // straight from the patient's own detail page, instead of requiring the
  // kid to separately log in with their PIN first -- the structural gap
  // identified 2026-08-13. `dest` picks the landing route directly rather
  // than relying on ProtectedKid's own assessment_completed redirect,
  // since "Launch Assessment" should go to /assessment even for a patient
  // who's already completed it (a therapist re-running it deliberately),
  // not get bounced to /play/levels by that redirect.
  const handleLaunchSession = async (dest) => {
    setLaunchingSession(dest)
    try {
      await startSupervisedSession(id)
      navigate(dest === 'assessment' ? '/assessment' : '/play')
    } catch (err) {
      console.error('Failed to launch session:', err)
      setReportError("Couldn't launch the session — please try again.")
    } finally {
      setLaunchingSession(null)
    }
  }

  const handleDownloadReport = async () => {
    setReportError('')
    setDownloadingReport(true)
    try {
      const response = await dashboardAPI.getReport(id)
      const url = URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `${data.first_name}_progress_report.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      // responseType: 'blob' means axios hands back a Blob even for error
      // responses — has to be read as text and re-parsed to get the real
      // `detail` message rather than showing "[object Blob]".
      let message = 'Could not generate the report — please try again.'
      if (err.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text()
          message = JSON.parse(text).detail || message
        } catch { /* fall back to the generic message above */ }
      }
      setReportError(message)
    } finally {
      setDownloadingReport(false)
    }
  }

  const applyIdeaToAssignment = (idea) => {
    setNewAssignment(n => ({ ...n, title: idea.title, instructions: idea.description }))
    setIdeasOpen(false)
  }

  const saveAssignment = async () => {
    if (!newAssignment.title.trim()) return
    setSavingAssignment(true)
    try {
      const payload = {
        ...newAssignment,
        level_id: newAssignment.level_id || null,
        instructions: newAssignment.instructions || null,
        due_at: newAssignment.due_at ? new Date(newAssignment.due_at).toISOString() : null,
      }
      const { data: created } = await dashboardAPI.createAssignment(id, payload)
      setAssignments(a => [created, ...a])
      setNewAssignment({ game: 'chime', level_id: '', title: '', instructions: '', due_at: '' })
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't save assignment — try again"))
    } finally {
      setSavingAssignment(false)
    }
  }

  const toggleAssignmentDone = async (a) => {
    const status = a.status === 'completed' ? 'assigned' : 'completed'
    try {
      const { data: updated } = await dashboardAPI.updateAssignment(a.id, { status })
      setAssignments(list => list.map(x => x.id === a.id ? updated : x))
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't update assignment — try again"))
    }
  }

  const removeAssignment = async (assignmentId) => {
    if (!window.confirm("Remove this assignment? This can't be undone.")) return
    try {
      await dashboardAPI.deleteAssignment(assignmentId)
      setAssignments(list => list.filter(a => a.id !== assignmentId))
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't remove assignment — try again"))
    }
  }

  const saveGoal = async () => {
    if (!newGoal.target_metric.trim() || !newGoal.target_value) return
    setSavingGoal(true)
    try {
      const payload = {
        target_metric: newGoal.target_metric,
        target_value: parseFloat(newGoal.target_value) / 100,
        target_date: newGoal.target_date ? new Date(newGoal.target_date).toISOString() : null,
      }
      const { data: created } = await dashboardAPI.createGoal(id, payload)
      setGoals(g => [created, ...g])
      setNewGoal({ target_metric: 'breath_consistency', target_value: '', target_date: '' })
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't save goal — try again"))
    } finally {
      setSavingGoal(false)
    }
  }

  const removeGoal = async (goalId) => {
    if (!window.confirm("Remove this goal? This can't be undone.")) return
    try {
      await dashboardAPI.deleteGoal(goalId)
      setGoals(list => list.filter(g => g.id !== goalId))
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't remove goal — try again"))
    }
  }

  const sendMessage = async () => {
    if (!newMessage.trim()) return
    setSendingMessage(true)
    try {
      const { data: sent } = await dashboardAPI.createMessage(id, { body: newMessage, sender_role: 'therapist' })
      setMessages(m => [...m, sent])
      setNewMessage('')
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't send message — try again"))
    } finally {
      setSendingMessage(false)
    }
  }

  const savePracticeLog = async () => {
    setSavingPractice(true)
    try {
      const payload = {
        practiced_on: new Date(newPractice.practiced_on).toISOString(),
        duration_minutes: newPractice.duration_minutes ? parseInt(newPractice.duration_minutes, 10) : null,
        notes: newPractice.notes || null,
      }
      const { data: created } = await dashboardAPI.createHomePractice(id, payload)
      setHomePractice(h => [created, ...h])
      setNewPractice({ practiced_on: new Date().toISOString().slice(0, 10), duration_minutes: '', notes: '' })
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't save practice log — try again"))
    } finally {
      setSavingPractice(false)
    }
  }

  const saveNote = async () => {
    if (!noteText.trim()) return
    setSavingNote(true)
    try {
      const { data: note } = await dashboardAPI.createNote(id, { content: noteText })
      setNotes(n => [note, ...n])
      setNoteText('')
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't save note — try again"))
    } finally {
      setSavingNote(false)
    }
  }

  if (loading) return <PageLoader />
  if (!data)   return <div className="p-8 text-white/50">Patient not found</div>

  const radarData = data.level_progress.map(l => ({
    level: LEVEL_EMOJIS[l.level_id] + ' ' + l.level_name.split(' ').slice(-1)[0],
    stars: l.best_stars,
    fullMark: 3,
  }))

  const barData = data.recent_sessions.slice().reverse().map((s, i) => ({
    name: `#${i + 1}`,
    stars: s.stars_earned || 0,
    breath: s.avg_breath_strength ? +(s.avg_breath_strength * 100).toFixed(0) : 0,
  }))

  const trend = data.improvement_trend
  const trendLabel = trend == null ? '—'
                   : trend > 0    ? `+${trend.toFixed(1)} ↑`
                   : trend < 0    ? `${trend.toFixed(1)} ↓`
                   : '→ Stable'
  const trendColor = trend > 0 ? 'text-brand-green' : trend < 0 ? 'text-brand-coral' : 'text-white/50'

  // Session-prep digest -- everything a therapist would otherwise dig for
  // across the Progress/Care tabs before a session, assembled from data
  // this page already loads (no new endpoint). goals/homePractice/
  // assignments are already sorted newest-first server-side.
  const prepGoal = goals.find(g => !g.achieved) || goals[0] || null
  const prepLastPractice = homePractice[0] || null
  const prepOverdueCount = assignments.filter(a => a.status === 'overdue').length
  const prepLastSession = data.recent_sessions[0]?.started_at || null

  // One ring per module, all from data already loaded elsewhere on this
  // page (no new endpoints) -- Orpheus doesn't expose a single accuracy
  // number, so it's attempts-weighted across manner/place/voicing here,
  // same shape as the per-category math in _accuracy_by on the backend.
  const orpheusAccuracy = (() => {
    if (!vmDashboard) return 0
    const rows = [...vmDashboard.manner_accuracy, ...vmDashboard.place_accuracy, ...vmDashboard.voicing_accuracy]
    const totalAttempts = rows.reduce((s, r) => s + r.attempts, 0)
    return totalAttempts ? rows.reduce((s, r) => s + r.accuracy * r.attempts, 0) / totalAttempts : 0
  })()

  const MODULE_RINGS = [
    {
      key: 'assessment', label: 'Assessment', icon: ClipboardCheck, color: '#7850DC',
      loading: loading,
      value: data.latest_assessment ? 100 : 0,
      caption: data.latest_assessment ? 'Complete' : 'Not started',
    },
    {
      key: 'breathquest', label: 'BreathQuest', icon: Wind, color: '#A8FF6F',
      loading: loading,
      value: data.completion_rate * 100,
      caption: `${data.total_stars}/${data.max_possible_stars} stars`,
    },
    {
      key: 'vhr', label: 'Voice Hurdle', icon: Dog, color: '#1D9E75',
      loading: vhrLoading,
      value: vhrSessions.length ? vhrSessions.reduce((s, x) => s + x.pitch_accuracy, 0) / vhrSessions.length : 0,
      caption: vhrSessions.length ? `${vhrSessions.length} races` : 'No races yet',
    },
    {
      key: 'chime', label: 'Chime', icon: Bell, color: '#FAC775',
      loading: chimeLoading,
      value: chimeError || !chimeEvents.length ? 0 : (chimeEvents.reduce((s, e) => s + e.score, 0) / chimeEvents.length) * 100,
      caption: chimeError ? 'Unavailable' : chimeEvents.length ? `${chimeEvents.length} attempts` : 'No attempts yet',
    },
    {
      key: 'orpheus', label: 'Orpheus', icon: Waves, color: '#6EC6E8',
      loading: vmLoading,
      value: vmError ? 0 : orpheusAccuracy,
      caption: vmError ? 'Unavailable' : vmDashboard?.sessions_count ? `${vmDashboard.sessions_count} sessions` : 'No sessions yet',
    },
    {
      key: 'flashcards', label: 'Flashcards', icon: ListChecks, color: '#F4B942',
      loading: flashcardsLoading,
      value: flashcardsError ? 0 : (flashcardsData?.overall_accuracy ?? 0),
      caption: flashcardsError ? 'Unavailable' : flashcardsData?.total_attempts ? `${flashcardsData.total_attempts} attempts` : 'No attempts yet',
    },
  ]

  const TABS = [
    ['progress', BarChart3, 'Progress'],
    ['sessions', Gamepad2, 'Sessions'],
    ['voicehurdlerace', Dog, 'Voice Hurdle'],
    ['chime', Bell, 'Chime'],
    ['vaakmirror', Waves, 'Orpheus'],
    ['flashcards', ListChecks, 'Flashcards'],
    ['care', HeartPulse, 'Care'],
    ['notes', FileText, 'Notes'],
  ]

  return (
    <div className="min-h-screen bg-brand-dark relative flex">
      {/* Same ambient glow as the therapist dashboard, so landing on a
          specific patient doesn't feel like a flatter, less-considered
          page than the dashboard just navigated from. */}
      <AmbientGlow />

      <Sidebar
        role="therapist"
        items={[
          { label: 'Dashboard', icon: LayoutDashboard, to: '/therapist/dashboard' },
          { label: 'Settings', icon: Settings, to: '/therapist/settings' },
        ]}
        name={therapist?.full_name}
        subtitle={therapist?.clinic_name}
        onLogout={logout}
        extraFooter={<AboutModal role="therapist" />}
      />

      <div className="relative flex-1 min-w-0">
      {/* Nav */}
      <nav className="relative border-b border-white/[0.08] px-6 py-4 flex items-center gap-4
                       sticky top-0 bg-brand-dark/85 backdrop-blur-xl z-10">
        <button onClick={() => navigate('/therapist/dashboard')}
                className="text-white/65 hover:text-white text-sm transition-colors">← Dashboard</button>
        <span className="text-white/20">/</span>
        <span className="text-white font-semibold">{data.first_name}</span>
        <div className="flex-1" />
        <Button variant="teal" size="sm" onClick={() => handleLaunchSession('assessment')} disabled={launchingSession !== null}>
          <ClipboardCheck size={14} className="mr-1.5 inline" />
          {launchingSession === 'assessment' ? 'Launching…' : 'Launch Assessment'}
        </Button>
        <Button variant="primary" size="sm" onClick={() => handleLaunchSession('play')} disabled={launchingSession !== null}>
          <Play size={14} className="mr-1.5 inline" />
          {launchingSession === 'play' ? 'Launching…' : 'Launch Live Therapy'}
        </Button>
        <Button
          variant="agent"
          size="sm"
          onClick={() => {
            const AGENT_GAMES = { chime: 'chime', voicehurdlerace: 'voicehurdlerace' }
            const game = AGENT_GAMES[tab] || 'breathquest'
            navigate(`/therapist/patients/${id}/agent?game=${game}`)
          }}
        >
          <Brain size={14} className="mr-1.5 inline" />
          What the agent sees
        </Button>
        <Button variant="ghost" size="sm" onClick={handleDownloadReport} disabled={downloadingReport}>
          <Download size={14} className="mr-1.5 inline" />
          {downloadingReport ? 'Generating…' : 'Download Report'}
        </Button>
      </nav>
      {reportError && (
        <div className="relative max-w-5xl mx-auto px-6 pt-4">
          <div className="bg-brand-coral/10 border border-brand-coral/30 rounded-xl px-4 py-3 text-brand-coral text-sm">
            {reportError}
          </div>
        </div>
      )}

      <div className="relative max-w-5xl mx-auto px-6 py-8">
        {/* Profile header */}
        <div className="flex items-center gap-6 mb-8">
          <div className="relative">
            <div className="absolute inset-0 rounded-full bg-brand-green/20 blur-xl" />
            <Avatar avatar={data.avatar} photoUrl={data.avatar_photo_url} size="xl" />
          </div>
          <div className="flex-1">
            <h1 className="font-display text-3xl font-bold text-white">{data.first_name}</h1>
            <div className="flex items-center gap-3 mt-2 flex-wrap">
              <Badge color="green">{data.total_sessions} sessions</Badge>
              <Badge color="amber">{data.total_stars} / {data.max_possible_stars} stars</Badge>
              <span className={`text-sm font-semibold ${trendColor}`}>Trend: {trendLabel}</span>
              <PlayerCodeChip code={data.player_code} />
            </div>
          </div>
        </div>

        {/* Session prep -- a quick digest of everything a therapist would
            otherwise dig for across the Progress/Care tabs before a
            session: recent trend, active goal, last home-practice note,
            overdue assignments. Everything here is already loaded
            elsewhere on this page, just surfaced in one place up front. */}
        <Card className="mb-8 border-brand-teal/20">
          <div className="flex items-center gap-2 mb-4">
            <ClipboardCheck size={16} className="text-brand-teal" />
            <p className="font-mono text-xs uppercase tracking-widest text-brand-teal">Session prep</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            <div className="flex items-start gap-2.5">
              <Clock size={14} className="text-white/30 mt-0.5 shrink-0" />
              <div>
                <p className="text-white/40 text-xs">Last session</p>
                <p className="text-white">{relativeDate(prepLastSession)} · trend <span className={trendColor}>{trendLabel}</span></p>
              </div>
            </div>
            <div className="flex items-start gap-2.5">
              <Target size={14} className="text-white/30 mt-0.5 shrink-0" />
              <div>
                <p className="text-white/40 text-xs">Active goal</p>
                {prepGoal ? (
                  <p className="text-white capitalize">
                    {prepGoal.target_metric.replace(/_/g, ' ')} — target {Math.round(prepGoal.target_value * 100)}%
                    {prepGoal.current_value != null ? `, currently ${Math.round(prepGoal.current_value * 100)}%` : ''}
                  </p>
                ) : (
                  <p className="text-white/30">No goal set yet</p>
                )}
              </div>
            </div>
            <div className="flex items-start gap-2.5">
              <MessageSquare size={14} className="text-white/30 mt-0.5 shrink-0" />
              <div>
                <p className="text-white/40 text-xs">Last home practice note</p>
                {prepLastPractice ? (
                  <p className="text-white">
                    {new Date(prepLastPractice.practiced_on).toLocaleDateString('en', { month: 'short', day: 'numeric' })}
                    {prepLastPractice.notes ? ` — "${prepLastPractice.notes}"` : ' — no note left'}
                  </p>
                ) : (
                  <p className="text-white/30">Nothing logged yet</p>
                )}
              </div>
            </div>
            <div className="flex items-start gap-2.5">
              <ListChecks size={14} className="text-white/30 mt-0.5 shrink-0" />
              <div>
                <p className="text-white/40 text-xs">Assignments</p>
                <p className={prepOverdueCount > 0 ? 'text-brand-coral' : 'text-white'}>
                  {prepOverdueCount > 0 ? `${prepOverdueCount} overdue` : 'None overdue'}
                </p>
              </div>
            </div>
          </div>
        </Card>

        {/* Module snapshot — one ring per module so a therapist can see at a
            glance what's been done and what hasn't, without clicking through
            every tab. Each ring pops in with a staggered entrance; values
            animate in via ProgressRing's own stroke-dashoffset transition. */}
        <div className="flex gap-3 overflow-x-auto pb-2 mb-8 -mx-1 px-1">
          {MODULE_RINGS.map((m, i) => (
            <div
              key={m.key}
              style={{ animationDelay: `${i * 0.07}s` }}
              className="animate-card-pop motion-reduce:!opacity-100 motion-reduce:animate-none shrink-0"
            >
              <Card
                className="flex flex-col items-center gap-2 px-4 py-4 w-32 transition-all duration-200
                           hover:-translate-y-0.5 hover:shadow-lg"
                style={{ borderTop: `2px solid ${m.color}` }}
              >
                <div className="flex items-center gap-1.5 text-white/50 text-xs font-semibold">
                  <m.icon size={12} style={{ color: m.color }} />
                  {m.label}
                </div>
                {m.loading ? (
                  <div className="w-14 h-14 flex items-center justify-center"><Spinner /></div>
                ) : (
                  <ProgressRing value={m.value} size={56} stroke={5} color={m.color} />
                )}
                <p className="text-white/30 text-[11px] text-center leading-tight">{m.caption}</p>
              </Card>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-white/[0.04] border border-white/[0.06] p-1 rounded-xl mb-6 w-fit overflow-x-auto">
          {TABS.map(([t, Icon, label]) => (
            <button key={t} onClick={() => setTab(t)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold transition-all whitespace-nowrap
                ${tab === t ? 'bg-brand-green text-brand-dark shadow-sm' : 'text-white/50 hover:text-white hover:bg-white/[0.04]'}`}>
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>

        {/* Progress tab */}
        {tab === 'progress' && (
          <div className="flex flex-col gap-6">
            {/* Today's Recommendation — surfaces the RL agent's latest
                per-level decision (see dashboard.py's get_patient_progress /
                chime_data_store.get_latest_decision). null when the child
                has no recent session for any level yet, or every level's
                decision predates this being tracked. */}
            {data.recommended_action && (
              <Card className="animate-card-pop motion-reduce:!opacity-100 motion-reduce:animate-none"
                    style={{ opacity: 0, borderLeft: '3px solid #A8FF6F' }}>
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-full bg-brand-green/15 flex items-center justify-center shrink-0">
                    <Lightbulb size={18} className="text-brand-green" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <h3 className="font-semibold text-white">Today's Recommendation</h3>
                      <Badge color={ACTION_STYLE[data.recommended_action]?.color || 'gray'}>
                        {ACTION_STYLE[data.recommended_action]?.label || data.recommended_action}
                      </Badge>
                      {data.recommendation_policy && (
                        <Badge color="purple">
                          {POLICY_LABEL[data.recommendation_policy] || data.recommendation_policy}
                        </Badge>
                      )}
                    </div>
                    <p className="text-white/60 text-sm">
                      {data.recommendation_message || 'No further detail from the agent for this decision.'}
                    </p>
                  </div>
                </div>
              </Card>
            )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <PhonemeSummaryCard summary={phonemeSummary} loading={phonemeSummaryLoading} error={phonemeSummaryError} />

              {/* Radar */}
              <Card className="animate-card-pop motion-reduce:!opacity-100 motion-reduce:animate-none"
                    style={{ opacity: 0, animationDelay: '0.05s' }}>
                <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                  <BarChart3 size={16} className="text-brand-green" />
                  Level Mastery
                </h3>
                <ResponsiveContainer width="100%" height={260}>
                  <RadarChart data={radarData}>
                    <defs>
                      <radialGradient id="radarFill" cx="50%" cy="50%" r="65%">
                        <stop offset="0%" stopColor="#A8FF6F" stopOpacity={0.55} />
                        <stop offset="100%" stopColor="#1D9E75" stopOpacity={0.12} />
                      </radialGradient>
                    </defs>
                    <PolarGrid stroke="rgba(255,255,255,0.1)" />
                    <PolarAngleAxis dataKey="level" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }} />
                    <Radar dataKey="stars" stroke="#A8FF6F" strokeWidth={2} fill="url(#radarFill)"
                           isAnimationActive animationDuration={700} animationEasing="ease-out" />
                  </RadarChart>
                </ResponsiveContainer>
              </Card>

              {/* Level breakdown */}
              <Card className="animate-card-pop motion-reduce:!opacity-100 motion-reduce:animate-none"
                    style={{ opacity: 0, animationDelay: '0.1s' }}>
                <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                  <Target size={16} className="text-brand-teal" />
                  Level Details
                </h3>
                <div className="flex flex-col gap-3">
                  {data.level_progress.map(l => (
                    <ExpandableLevelRow key={l.level_id} level={l} sessions={data.recent_sessions || []}>
                      <div className="relative shrink-0">
                        <LevelIcon id={l.level_id} className="w-7 h-7" />
                        {l.best_stars === 3 && (
                          <span className="absolute -top-1.5 -right-1.5 text-[10px]" title="Maxed out">✨</span>
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-white/70">{l.level_name}</span>
                          <StarRating stars={l.best_stars} size="sm" />
                        </div>
                        <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                          <div className="h-full rounded-full transition-all duration-500"
                               style={{
                                 width: `${(l.best_stars / 3) * 100}%`,
                                 background: 'linear-gradient(90deg, #1D9E75, #A8FF6F)',
                               }} />
                        </div>
                      </div>
                      <span className="text-white/30 text-xs w-14 text-right">{l.attempts} tries</span>
                    </ExpandableLevelRow>
                  ))}
                </div>
              </Card>

              {/* Session trend bar chart */}
              {barData.length > 0 && (
                <Card className="md:col-span-2 animate-card-pop motion-reduce:!opacity-100 motion-reduce:animate-none"
                      style={{ opacity: 0, animationDelay: '0.15s' }}>
                  <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                    <Activity size={16} className="text-brand-amber" />
                    Recent Session Stars
                  </h3>
                  <ResponsiveContainer width="100%" height={160}>
                    <BarChart data={barData}>
                      <defs>
                        <linearGradient id="barFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#A8FF6F" />
                          <stop offset="100%" stopColor="#1D9E75" />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="name" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis domain={[0, 3]} ticks={[0,1,2,3]} tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={{ background: '#1E1E3F', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                               labelStyle={{ color: 'rgba(255,255,255,0.5)' }} itemStyle={{ color: '#A8FF6F' }} />
                      <Bar dataKey="stars" fill="url(#barFill)" radius={[4,4,0,0]}
                           isAnimationActive animationDuration={600} animationEasing="ease-out" />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              )}

              {/* Sound accuracy over time — real data from VaakMirror Attempts +
                  Chime session_events. No vocabulary-size or fluency-rate chart
                  here since neither is tracked anywhere in this app; showing
                  only what's actually measured rather than approximating. */}
              <Card className="md:col-span-2 animate-card-pop motion-reduce:!opacity-100 motion-reduce:animate-none"
                    style={{ opacity: 0, animationDelay: '0.2s' }}>
                <h3 className="font-semibold text-white mb-1 flex items-center gap-2">
                  <Waves size={16} className="text-[#6EC6E8]" />
                  Sound Accuracy Over Time
                </h3>
                <p className="text-white/30 text-xs mb-4">
                  Weekly accuracy per sound, from VaakMirror + Chime attempts (last 8 weeks)
                </p>
                {soundProgressLoading ? (
                  <div className="h-40 flex items-center justify-center"><Spinner /></div>
                ) : !soundProgress || Object.keys(soundProgress.sounds).length === 0 ? (
                  <div className="flex flex-col items-center gap-2 py-8">
                    <Waves size={28} className="text-white/20" />
                    <p className="text-white/30 text-sm text-center max-w-xs">
                      Not enough sound-level practice data yet — this fills in as {data.first_name} plays
                      VaakMirror or Chime.
                    </p>
                  </div>
                ) : (() => {
                  const COLORS = ['#A8FF6F', '#FAC775', '#6EC6E8', '#E24B4A', '#B08CE0']
                  const topSounds = Object.entries(soundProgress.sounds)
                    .sort((a, b) => b[1].reduce((s, p) => s + p.attempts, 0) - a[1].reduce((s, p) => s + p.attempts, 0))
                    .slice(0, 5)
                    .map(([sound]) => sound)
                  const soundColor = {}
                  topSounds.forEach((s, i) => { soundColor[s] = COLORS[i % COLORS.length] })
                  const weekSet = new Set()
                  topSounds.forEach(s => soundProgress.sounds[s].forEach(p => weekSet.add(p.week)))
                  const weeks = [...weekSet].sort()
                  const chartData = weeks.map(week => {
                    const row = { week: week.split('-W')[1] ? `W${week.split('-W')[1]}` : week }
                    topSounds.forEach(sound => {
                      const point = soundProgress.sounds[sound].find(p => p.week === week)
                      row[sound] = point ? Math.round(point.accuracy * 100) : null
                    })
                    return row
                  })

                  // Per-sound trend (second half of the 8-week window vs first
                  // half) and current value, so the strip can surface sounds
                  // that are declining or lowest-performing first -- the ones
                  // most worth a therapist's attention -- rather than listing
                  // alphabetically or by raw attempt count.
                  const avg = (arr) => arr.reduce((s, v) => s + v, 0) / arr.length
                  const soundStats = topSounds.map(sound => {
                    const points = chartData.map(r => r[sound]).filter(v => v != null)
                    const current = points.length ? points[points.length - 1] : null
                    let trend = null
                    if (points.length >= 2) {
                      const mid = Math.ceil(points.length / 2)
                      trend = Math.round(avg(points.slice(mid)) - avg(points.slice(0, mid)))
                    }
                    return { sound, current, trend }
                  }).sort((a, b) => {
                    const at = a.trend ?? 0
                    const bt = b.trend ?? 0
                    if (at !== bt) return at - bt
                    return (a.current ?? 100) - (b.current ?? 100)
                  })

                  const toggleSound = (sound) => setSelectedSound(s => s === sound ? null : sound)

                  return (
                    <>
                      <div className="flex flex-wrap gap-1.5 mb-3">
                        {soundStats.map(({ sound, current, trend }) => {
                          const isSelected = selectedSound === sound
                          const isDimmed = selectedSound && !isSelected
                          return (
                            <button
                              key={sound}
                              onClick={() => toggleSound(sound)}
                              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs transition-all
                                ${isSelected ? 'border-white/30 bg-white/10' : 'border-white/10 bg-white/[0.03] hover:bg-white/[0.06]'}
                                ${isDimmed ? 'opacity-40' : 'opacity-100'}`}
                            >
                              <span className="w-2 h-2 rounded-full shrink-0" style={{ background: soundColor[sound] }} />
                              <span className="text-white/80 font-medium">{sound}</span>
                              <span className="text-white/40">{current != null ? `${current}%` : '—'}</span>
                              {trend != null && trend !== 0 && (
                                <span className={trend > 0 ? 'text-brand-green' : 'text-brand-coral'}>
                                  {trend > 0 ? '↑' : '↓'}{Math.abs(trend)}
                                </span>
                              )}
                            </button>
                          )
                        })}
                        {selectedSound && (
                          <button onClick={() => setSelectedSound(null)}
                                  className="text-white/30 hover:text-white/60 text-xs px-2 py-1">
                            Show all
                          </button>
                        )}
                      </div>
                      <ResponsiveContainer width="100%" height={200}>
                        <LineChart data={chartData}>
                          <XAxis dataKey="week" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} axisLine={false} tickLine={false} />
                          <YAxis domain={[0, 100]} tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} axisLine={false} tickLine={false} />
                          <Tooltip contentStyle={{ background: '#1E1E3F', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                                   labelStyle={{ color: 'rgba(255,255,255,0.5)' }} formatter={(v) => v == null ? 'no data' : `${v}%`} />
                          <Legend
                            wrapperStyle={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', cursor: 'pointer' }}
                            onClick={(e) => toggleSound(e.dataKey)}
                          />
                          {topSounds.map((sound) => (
                            <Line key={sound} type="monotone" dataKey={sound} stroke={soundColor[sound]}
                                  strokeWidth={selectedSound === sound ? 3 : 2}
                                  strokeOpacity={selectedSound && selectedSound !== sound ? 0.15 : 1}
                                  dot={selectedSound && selectedSound !== sound ? false : { r: 3 }}
                                  connectNulls />
                          ))}
                        </LineChart>
                      </ResponsiveContainer>
                    </>
                  )
                })()}
              </Card>
              </div>
          </div>
        )}

        {/* Sessions tab */}
        {tab === 'sessions' && (
          <div className="flex flex-col gap-3">
            {data.recent_sessions.length === 0
              ? <Card className="text-center py-12 text-white/40">No sessions yet</Card>
              : data.recent_sessions.map(s => (
                <Card key={s.id} className="flex items-center gap-4">
                  <LevelIcon id={s.level_id} className="w-9 h-9" />
                  <div className="flex-1">
                    <p className="font-semibold text-white capitalize">{s.level_id.replace('_', ' ')}</p>
                    <p className="text-white/30 text-xs">
                      {new Date(s.started_at).toLocaleString()} ·{' '}
                      {s.duration_seconds ? `${Math.round(s.duration_seconds)}s` : 'N/A'}
                    </p>
                  </div>
                  <StarRating stars={s.stars_earned || 0} size="sm" />
                  <Badge color={s.completed ? 'green' : 'gray'}>
                    {s.completed ? 'Done' : 'Quit'}
                  </Badge>
                </Card>
              ))}
          </div>
        )}

        {/* Voice Hurdle Race tab — separate table/endpoint from BreathQuest,
            so this is intentionally self-contained rather than mixed into
            the stats above. */}
        {tab === 'voicehurdlerace' && (
          <div className="flex flex-col gap-4">
            {vhrLoading ? (
              <Card className="text-center py-12"><Spinner /></Card>
            ) : vhrSessions.length === 0 ? (
              <Card className="text-center py-12">
                <Dog size={28} className="text-white/20 mx-auto mb-2" />
                <p className="text-white/40">No Voice Hurdle Race sessions yet</p>
              </Card>
            ) : (
              <>
                <div className="grid grid-cols-3 gap-4">
                  <Card className="text-center">
                    <p className="text-2xl font-bold font-display text-brand-green">{vhrSessions.length}</p>
                    <p className="text-white/30 text-xs">races</p>
                  </Card>
                  <Card className="text-center">
                    <p className="text-2xl font-bold font-display text-yellow-400">
                      {Math.max(...vhrSessions.map(s => s.stars))}
                    </p>
                    <p className="text-white/30 text-xs">best stars</p>
                  </Card>
                  <Card className="text-center flex flex-col items-center justify-center">
                    <ProgressRing
                      value={vhrSessions.reduce((sum, s) => sum + s.pitch_accuracy, 0) / vhrSessions.length}
                      size={64}
                      color="#1D9E75"
                      label="avg pitch accuracy"
                    />
                  </Card>
                </div>
                {vhrSessions.map(s => (
                  <Card key={s.id} className="flex items-center gap-4">
                    <span className="text-2xl">🐶</span>
                    <div className="flex-1">
                      <p className="font-semibold text-white">{s.level_name}</p>
                      <p className="text-white/30 text-xs">
                        {new Date(s.created_at).toLocaleString()} · score {s.score}
                      </p>
                    </div>
                    <StarRating stars={s.stars} size="sm" />
                  </Card>
                ))}
              </>
            )}
          </div>
        )}

        {/* Chime tab — SQLite-backed, bridged read-only via chimeAPI.
            No stars/score concept here, just raw phoneme attempt scores
            (0.0-1.0), so this is deliberately a plain event log rather
            than forcing it into the star-rating visuals used elsewhere. */}
        {tab === 'chime' && (
          <div className="flex flex-col gap-4">
            {chimeLoading ? (
              <Card className="text-center py-12"><Spinner /></Card>
            ) : chimeError ? (
              <Card className="text-center py-12">
                <CloudOff size={28} className="text-brand-coral/70 mx-auto mb-2" />
                <p className="text-white/40">Couldn't load Chime data — the Chime service may be unavailable right now.</p>
              </Card>
            ) : chimeEvents.length === 0 ? (
              <Card className="text-center py-12">
                <Bell size={28} className="text-white/20 mx-auto mb-2" />
                <p className="text-white/40">No Chime sessions yet</p>
              </Card>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <Card className="text-center">
                    <p className="text-2xl font-bold font-display text-brand-green">{chimeEvents.length}</p>
                    <p className="text-white/30 text-xs">attempts logged</p>
                  </Card>
                  <Card className="text-center">
                    <p className="text-2xl font-bold font-display text-brand-teal">
                      {Math.round((chimeEvents.reduce((sum, e) => sum + e.score, 0) / chimeEvents.length) * 100)}%
                    </p>
                    <p className="text-white/30 text-xs">avg phoneme score</p>
                  </Card>
                </div>
                {chimeEvents.slice().reverse().slice(0, 20).map(e => (
                  <Card key={e.id} className="flex items-center gap-4">
                    <span className="text-2xl">🔔</span>
                    <div className="flex-1">
                      <p className="font-semibold text-white capitalize">{e.level_id.replace('_', ' ')}</p>
                      <p className="text-white/30 text-xs">
                        {new Date(e.timestamp).toLocaleString()} · attempt #{e.attempt_number}
                      </p>
                    </div>
                    <Badge color={e.is_valid_attempt ? 'green' : 'gray'}>
                      {Math.round(e.score * 100)}%
                    </Badge>
                  </Card>
                ))}
              </>
            )}
          </div>
        )}

        {/* VaakMirror tab — uses its own already-built therapist dashboard
            endpoint directly rather than re-deriving stats client-side. */}
        {tab === 'vaakmirror' && (
          <div className="flex flex-col gap-4">
            {/* Agent suggestions — the same adaptive-difficulty agent behind
                Chime and BreathQuest, applied here to round_size. Purely
                advisory: nothing changes until the therapist hits Accept. */}
            {!agentLoading && VM_GAMES.some(g => agentSuggestions[g] && agentSuggestions[g].action !== 'hold' && !dismissedSuggestions[g]) && (
              <div className="flex flex-col gap-2">
                {VM_GAMES.filter(g => agentSuggestions[g] && agentSuggestions[g].action !== 'hold' && !dismissedSuggestions[g]).map(g => {
                  const s = agentSuggestions[g]
                  return (
                    <Card key={g} className="border border-brand-teal/30 bg-brand-teal/5">
                      <div className="flex items-start gap-3">
                        <span className="text-lg leading-none mt-0.5" title="Adaptive agent">🧠</span>
                        <div className="flex-1">
                          <p className="text-white text-sm font-medium">{VM_GAME_LABELS[g]}</p>
                          <p className="text-white/50 text-xs mt-0.5">{s.message}</p>
                          <p className="text-white/30 text-xs mt-1">
                            Suggests round size {s.current_round_size} → {s.suggested_round_size}
                            {' '}(based on {s.n_events_considered} recent sessions)
                          </p>
                        </div>
                        <div className="flex gap-2 shrink-0">
                          <Button
                            size="sm"
                            onClick={() => acceptAgentSuggestion(g)}
                            disabled={applyingSuggestion === g}
                          >
                            {applyingSuggestion === g ? '…' : 'Accept'}
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => dismissAgentSuggestion(g)}>
                            Dismiss
                          </Button>
                        </div>
                      </div>
                    </Card>
                  )
                })}
              </div>
            )}

            {vmLoading ? (
              <Card className="text-center py-12"><Spinner /></Card>
            ) : vmError ? (
              <Card className="text-center py-12">
                <CloudOff size={28} className="text-brand-coral/70 mx-auto mb-2" />
                <p className="text-white/40">Couldn't load Orpheus data — the Orpheus service may be unavailable right now.</p>
              </Card>
            ) : !vmDashboard || vmDashboard.sessions_count === 0 ? (
              <Card className="text-center py-12">
                <Waves size={28} className="text-white/20 mx-auto mb-2" />
                <p className="text-white/40">No Orpheus sessions yet</p>
              </Card>
            ) : (
              <>
                <Card className="text-center">
                  <p className="text-2xl font-bold font-display text-brand-green">{vmDashboard.sessions_count}</p>
                  <p className="text-white/30 text-xs">sessions</p>
                </Card>

                {!attemptsLoading && attempts.length > 0 && (
                  <Card>
                    <h3 className="font-semibold text-white mb-3">Labeling Queue</h3>
                    <div className="flex flex-col gap-2">
                      {attempts.map(a => (
                        <div key={a.id} className="flex items-center gap-3 border-b border-white/5 pb-2 last:border-0">
                          <Badge color={TIER_COLORS[a.predicted_tier] || 'gray'}>{a.predicted_tier || '—'}</Badge>
                          <div className="flex-1">
                            <p className="text-white text-sm capitalize">{a.shape || 'unknown shape'}</p>
                            <p className="text-white/30 text-xs">{new Date(a.created_at).toLocaleDateString()}</p>
                          </div>
                          <button
                            onClick={() => labelAttempt(a.id, 'correct')}
                            disabled={labelingId === a.id}
                            className="text-brand-green hover:text-brand-green/70 disabled:opacity-30"
                            title="Correct"
                          >
                            <Check size={16} />
                          </button>
                          <button
                            onClick={() => labelAttempt(a.id, 'incorrect')}
                            disabled={labelingId === a.id}
                            className="text-brand-coral hover:text-brand-coral/70 disabled:opacity-30"
                            title="Incorrect"
                          >
                            <X size={16} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}

                {vmDashboard.flagged_gaps.length > 0 && (
                  <Card>
                    <h3 className="font-semibold text-white mb-3">Flagged Gaps</h3>
                    <div className="flex flex-col gap-2">
                      {vmDashboard.flagged_gaps.map(g => (
                        <div key={g.id} className="flex items-start gap-3">
                          <Badge color={g.severity === 'high' ? 'coral' : g.severity === 'medium' ? 'amber' : 'gray'}>
                            {g.severity}
                          </Badge>
                          <div className="flex-1">
                            <p className="text-white text-sm font-medium">{g.title}</p>
                            <p className="text-white/40 text-xs">{g.detail}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}

                {[['Manner', vmDashboard.manner_accuracy], ['Place', vmDashboard.place_accuracy], ['Voicing', vmDashboard.voicing_accuracy]].map(([label, rows]) => (
                  rows.length > 0 && (
                    <Card key={label}>
                      <h3 className="font-semibold text-white mb-3">{label} Accuracy</h3>
                      <div className="flex flex-col gap-2">
                        {rows.map(r => (
                          <div key={r.category} className="flex items-center gap-3">
                            <span className="text-sm text-white/70 w-24 capitalize">{r.category}</span>
                            <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                              <div className="h-full bg-brand-teal rounded-full" style={{ width: `${r.accuracy}%` }} />
                            </div>
                            <span className="text-white/40 text-xs w-16 text-right">{r.accuracy}% ({r.attempts})</span>
                          </div>
                        ))}
                      </div>
                    </Card>
                  )
                ))}
              </>
            )}
          </div>
        )}

        {/* Flashcards tab — phoneme-level mastery, strongest/weakest highlights,
            and a recent-words feed. No stars concept, same as Chime. */}
        {tab === 'flashcards' && (
          <div className="flex flex-col gap-6">
            {flashcardsLoading ? (
              <Card className="text-center py-12"><Spinner /></Card>
            ) : flashcardsError ? (
              <Card className="text-center py-12">
                <CloudOff size={28} className="text-brand-coral/70 mx-auto mb-2" />
                <p className="text-white/40">Couldn't load Flashcards data — the Flashcards service may be unavailable right now.</p>
              </Card>
            ) : !flashcardsData || flashcardsData.total_attempts === 0 ? (
              <Card className="text-center py-12">
                <ListChecks size={28} className="text-white/20 mx-auto mb-2" />
                <p className="text-white/40">No Flashcards sessions yet</p>
              </Card>
            ) : (
              <>
                <div className="grid grid-cols-3 gap-4">
                  <Card className="text-center">
                    <p className="text-2xl font-bold font-display text-brand-green">{flashcardsData.total_attempts}</p>
                    <p className="text-white/30 text-xs">attempts</p>
                  </Card>
                  <Card className="text-center">
                    <p className="text-2xl font-bold font-display text-brand-teal">{flashcardsData.distinct_phonemes_practiced}</p>
                    <p className="text-white/30 text-xs">phonemes practiced</p>
                  </Card>
                  <Card className="text-center">
                    <p className="text-2xl font-bold font-display text-yellow-400">{flashcardsData.overall_accuracy}%</p>
                    <p className="text-white/30 text-xs">overall accuracy</p>
                  </Card>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card>
                    <h3 className="font-semibold text-white mb-3">Strongest Sounds</h3>
                    <div className="flex flex-wrap gap-2">
                      {flashcardsData.strongest.length === 0 ? (
                        <p className="text-white/30 text-xs">Not enough data yet</p>
                      ) : flashcardsData.strongest.map(p => (
                        <PhonemePill key={p.phoneme} p={p} tone="green" />
                      ))}
                    </div>
                  </Card>
                  <Card>
                    <h3 className="font-semibold text-white mb-3">Needs Practice</h3>
                    <div className="flex flex-wrap gap-2">
                      {flashcardsData.weakest.length === 0 ? (
                        <p className="text-white/30 text-xs">Not enough data yet</p>
                      ) : flashcardsData.weakest.map(p => (
                        <PhonemePill key={p.phoneme} p={p} tone="coral" />
                      ))}
                    </div>
                  </Card>
                </div>

                <Card>
                  <h3 className="font-semibold text-white mb-3">All Phonemes</h3>
                  <div className="flex flex-col gap-3">
                    {flashcardsData.mastery.map(p => (
                      <div key={p.phoneme} className="flex items-center gap-3">
                        <span className="text-white/80 font-mono text-sm w-10 uppercase">{p.phoneme}</span>
                        <div className="flex-1">
                          <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                            <div className="h-full bg-brand-green rounded-full transition-all"
                                 style={{ width: `${p.accuracy}%` }} />
                          </div>
                        </div>
                        <span className="text-white/50 text-xs w-12 text-right">{p.accuracy}%</span>
                        <span className="text-white/30 text-xs w-16 text-right">{p.attempts} tries</span>
                        {p.trend && (
                          <span className={`text-xs w-4 ${p.trend === 'up' ? 'text-brand-green' : p.trend === 'down' ? 'text-brand-coral' : 'text-white/30'}`}>
                            {p.trend === 'up' ? '↑' : p.trend === 'down' ? '↓' : '→'}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </Card>

                {flashcardsData.recent_words.length > 0 && (
                  <Card>
                    <h3 className="font-semibold text-white mb-3">Recently Practiced Words</h3>
                    <div className="flex flex-wrap gap-2">
                      {flashcardsData.recent_words.map((w, i) => (
                        <span key={i} className="badge bg-white/5 text-white/70 text-xs px-2.5 py-1 rounded-full">{w}</span>
                      ))}
                    </div>
                  </Card>
                )}
              </>
            )}
          </div>
        )}

        {/* Care tab — Assignments, Goals, Messages, Home Practice, and the
            rule-based Weekly Summary. Kept as one tab rather than four
            since a therapist reviewing a patient wants all of this
            together in one "how's care going" pass. */}
        {tab === 'care' && (
          <div className="flex flex-col gap-6">
            {/* Weekly summary */}
            <Card>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-white">Weekly Summary</h3>
                <div className="flex items-center gap-2">
                  <button onClick={() => setWeekOffset(w => w + 1)}
                          className="flex items-center gap-1 text-white/40 hover:text-white text-xs px-2 py-1 rounded transition-colors">
                    <ChevronLeft size={13} /> Prior week
                  </button>
                  <span className="text-white/30 text-xs">{weekOffset === 0 ? 'This week' : `${weekOffset} week${weekOffset === 1 ? '' : 's'} ago`}</span>
                  <button onClick={() => setWeekOffset(w => Math.max(0, w - 1))} disabled={weekOffset === 0}
                          className="flex items-center gap-1 text-white/40 hover:text-white text-xs px-2 py-1 rounded transition-colors disabled:opacity-20">
                    Next week <ChevronRight size={13} />
                  </button>
                </div>
              </div>
              {summaryLoading ? (
                <div className="py-8 text-center"><Spinner /></div>
              ) : !weeklySummary ? (
                <p className="text-white/40 text-sm">Couldn't load the weekly summary.</p>
              ) : (
                <>
                  <div className="grid grid-cols-3 gap-x-4 gap-y-3 mb-4">
                    {[
                      ['BreathQuest', weeklySummary.stats.bq_sessions],
                      ['— completed', weeklySummary.stats.bq_completed],
                      ['Chime attempts', weeklySummary.stats.chime_attempts],
                      ['Assignments done', weeklySummary.stats.assignments_completed],
                      ['Assignments overdue', weeklySummary.stats.assignments_overdue],
                      ['Goals open', weeklySummary.stats.goals_open],
                      ['Goals achieved', weeklySummary.stats.goals_achieved_total],
                      ['Practice days', `${weeklySummary.stats.home_practice_days}/7`],
                      ['Practice minutes', weeklySummary.stats.home_practice_minutes],
                    ].map(([label, value], i) => (
                      <div key={i}>
                        <p className="text-lg font-bold text-white leading-tight">{value}</p>
                        <p className="text-white/40 text-[11px] leading-tight">{label}</p>
                      </div>
                    ))}
                  </div>
                  {weeklySummary.highlights.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {weeklySummary.highlights.map((h, i) => (
                        <span key={i} className="badge bg-white/5 text-white/70 text-xs px-2 py-1 rounded-full">{h}</span>
                      ))}
                    </div>
                  )}
                </>
              )}
            </Card>

            {careLoading ? (
              <Card className="text-center py-12"><Spinner /></Card>
            ) : careError ? (
              <Card className="text-center py-12 text-white/40">Couldn't load Care data right now.</Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Goals */}
                <Card>
                  <h3 className="font-semibold text-white mb-3">Goals</h3>
                  <div className="flex flex-col gap-2 mb-4">
                    {goals.length === 0 && (
                      <div className="flex items-center gap-2 text-white/30 text-sm py-1.5">
                        <Target size={14} className="text-white/20 shrink-0" />
                        No goals set yet
                      </div>
                    )}
                    {goals.map(g => (
                      <div key={g.id} className="border-b border-white/5 pb-2 last:border-0">
                        <ExpandableGoalRow goal={g}>
                          <div className="flex-1">
                            <p className="text-white text-sm capitalize">{g.target_metric.replace(/_/g, ' ')}</p>
                            <p className="text-white/30 text-xs">
                              target {Math.round(g.target_value * 100)}%{g.current_value != null ? ` · current ${Math.round(g.current_value * 100)}%` : ''}
                            </p>
                          </div>
                          <Badge color={g.achieved ? 'green' : 'gray'}>{g.achieved ? 'Achieved' : 'In progress'}</Badge>
                          <button onClick={(e) => { e.stopPropagation(); removeGoal(g.id) }} className="text-white/45 hover:text-brand-coral"><X size={14} /></button>
                        </ExpandableGoalRow>
                      </div>
                    ))}
                  </div>
                  <div className="flex flex-col gap-2">
                    <div className="flex flex-wrap gap-1.5">
                      {GOAL_PRESETS.map(preset => (
                        <button
                          key={preset.label}
                          type="button"
                          onClick={() => setNewGoal({
                            target_metric: preset.target_metric,
                            target_value: preset.target_value,
                            target_date: presetTargetDate(preset.weeks),
                          })}
                          className="text-[11px] font-medium px-2.5 py-1 rounded-full bg-white/5 border border-white/10
                                     text-white/50 hover:text-white hover:bg-white/10 hover:border-white/20 transition-colors"
                        >
                          {preset.label}
                        </button>
                      ))}
                    </div>
                    <select className="input text-sm" value={newGoal.target_metric}
                            onChange={e => setNewGoal(n => ({ ...n, target_metric: e.target.value }))}>
                      <option value="breath_consistency">Breath Consistency</option>
                      <option value="avg_breath_strength">Average Breath Strength</option>
                    </select>
                    <div className="flex gap-2">
                      <input className="input text-sm" type="number" min="0" max="100" step="1" placeholder="Target %"
                             value={newGoal.target_value}
                             onChange={e => setNewGoal(n => ({ ...n, target_value: e.target.value }))} />
                      <input className="input text-sm" type="date"
                             min={new Date().toISOString().slice(0, 10)}
                             value={newGoal.target_date}
                             onChange={e => setNewGoal(n => ({ ...n, target_date: e.target.value }))} />
                    </div>
                    <Button onClick={saveGoal} disabled={savingGoal || !newGoal.target_metric.trim() || !newGoal.target_value} size="sm">
                      {savingGoal ? 'Saving…' : 'Add Goal'}
                    </Button>
                  </div>
                </Card>

                {/* Home practice ideas library — 50 items, filterable by
                    condition/goal. "Use for assignment" pre-fills the
                    Assignments form below. */}
                <Card>
                  <button onClick={() => setIdeasOpen(o => !o)}
                          className="w-full flex items-center justify-between">
                    <h3 className="font-semibold text-white">Home Practice Ideas</h3>
                    <span className="text-white/40 text-sm">{ideasOpen ? '− Hide' : '+ Browse 50 ideas'}</span>
                  </button>
                  {ideasOpen && (
                    <div className="mt-4">
                      <select className="input text-sm mb-3" value={ideaCondition}
                              onChange={e => setIdeaCondition(e.target.value)}>
                        <option value="">All conditions</option>
                        <option value="articulation">Articulation</option>
                        <option value="phonological">Phonological</option>
                        <option value="language">Language</option>
                        <option value="fluency">Fluency</option>
                        <option value="voice">Voice</option>
                        <option value="oral-motor">Oral motor</option>
                      </select>
                      {ideasLoading ? (
                        <div className="py-6 text-center"><Spinner /></div>
                      ) : (
                        <div className="flex flex-col gap-2 max-h-80 overflow-y-auto">
                          {ideas.map(idea => (
                            <div key={idea.id} className="border-b border-white/5 pb-2 last:border-0">
                              <p className="text-white text-sm font-medium">{idea.title}</p>
                              <p className="text-white/40 text-xs mt-0.5 mb-1.5">{idea.description}</p>
                              <button onClick={() => applyIdeaToAssignment(idea)}
                                      className="text-brand-green text-xs hover:underline">
                                Use for assignment →
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </Card>

                {/* Assignments */}
                <Card>
                  <h3 className="font-semibold text-white mb-3">Assignments</h3>
                  <div className="flex flex-col gap-2 mb-4">
                    {assignments.length === 0 && (
                      <div className="flex items-center gap-2 text-white/30 text-sm py-1.5">
                        <ListChecks size={14} className="text-white/20 shrink-0" />
                        No assignments yet
                      </div>
                    )}
                    {assignments.map(a => (
                      <div key={a.id} className="border-b border-white/5 pb-2 last:border-0">
                        <ExpandableAssignmentRow assignment={a}>
                          <div className="flex-1">
                            <p className="text-white text-sm">{a.title}</p>
                            <p className="text-white/30 text-xs capitalize">
                              {a.game}{a.level_id ? ` · ${a.level_id}` : ''}
                              {a.due_at ? ` · due ${new Date(a.due_at).toLocaleDateString()}` : ''}
                            </p>
                          </div>
                          <Badge color={a.status === 'completed' ? 'green' : a.status === 'overdue' ? 'coral' : 'gray'}>
                            {a.status}
                          </Badge>
                          <button onClick={(e) => { e.stopPropagation(); toggleAssignmentDone(a) }} className="text-white/65 hover:text-brand-green text-xs">
                            {a.status === 'completed' ? 'Undo' : 'Done'}
                          </button>
                          <button onClick={(e) => { e.stopPropagation(); removeAssignment(a.id) }} className="text-white/45 hover:text-brand-coral"><X size={14} /></button>
                        </ExpandableAssignmentRow>
                      </div>
                    ))}
                  </div>
                  <div className="flex flex-col gap-2">
                    <input className="input text-sm" placeholder="Title"
                           value={newAssignment.title}
                           onChange={e => setNewAssignment(n => ({ ...n, title: e.target.value }))} />
                    <textarea className="input text-sm resize-none" rows={2} placeholder="Instructions (optional)"
                           value={newAssignment.instructions}
                           onChange={e => setNewAssignment(n => ({ ...n, instructions: e.target.value }))} />
                    <div className="flex gap-2">
                      <select className="input text-sm" value={newAssignment.game}
                              onChange={e => setNewAssignment(n => ({ ...n, game: e.target.value }))}>
                        <option value="chime">Chime</option>
                        <option value="breathquest">BreathQuest</option>
                        <option value="vaakmirror">Orpheus</option>
                        <option value="voicehurdlerace">Voice Hurdle Race</option>
                      </select>
                      <input className="input text-sm" placeholder="Level id (optional)"
                             value={newAssignment.level_id}
                             onChange={e => setNewAssignment(n => ({ ...n, level_id: e.target.value }))} />
                    </div>
                    <input className="input text-sm" type="date"
                           min={new Date().toISOString().slice(0, 10)}
                           value={newAssignment.due_at}
                           onChange={e => setNewAssignment(n => ({ ...n, due_at: e.target.value }))} />
                    <Button onClick={saveAssignment} disabled={savingAssignment || !newAssignment.title.trim()} size="sm">
                      {savingAssignment ? 'Saving…' : 'Add Assignment'}
                    </Button>
                  </div>
                </Card>

                {/* Messages */}
                <Card>
                  <h3 className="font-semibold text-white mb-3">Messages</h3>
                  <div className="flex flex-col gap-2 mb-3 max-h-64 overflow-y-auto">
                    {messages.length === 0 && (
                      <div className="flex items-center gap-2 text-white/30 text-sm py-1.5">
                        <MessageSquare size={14} className="text-white/20 shrink-0" />
                        No messages yet
                      </div>
                    )}
                    {messages.map(m => (
                      <div key={m.id} className={`text-sm rounded-lg px-3 py-2 max-w-[85%] ${
                        m.sender_role === 'therapist' ? 'bg-brand-green/20 text-white self-end ml-auto' : 'bg-white/10 text-white'
                      }`}>
                        <p>{m.body}</p>
                        <p className="text-white/30 text-[10px] mt-1">
                          {m.sender_role} · {new Date(m.created_at).toLocaleString()}{m.read_at ? ' · read' : ''}
                        </p>
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input className="input text-sm flex-1" placeholder="Message to parent…"
                           value={newMessage}
                           onChange={e => setNewMessage(e.target.value)}
                           onKeyDown={e => e.key === 'Enter' && sendMessage()} />
                    <Button onClick={sendMessage} disabled={sendingMessage || !newMessage.trim()} size="sm">Send</Button>
                  </div>
                </Card>

                {/* Home Practice */}
                <Card>
                  <h3 className="font-semibold text-white mb-3">Home Practice Log</h3>
                  <div className="flex flex-col gap-2 mb-4 max-h-64 overflow-y-auto">
                    {homePractice.length === 0 && (
                      <div className="flex items-center gap-2 text-white/30 text-sm py-1.5">
                        <Activity size={14} className="text-white/20 shrink-0" />
                        No home practice logged yet
                      </div>
                    )}
                    {homePractice.map(h => (
                      <div key={h.id} className="border-b border-white/5 pb-2 last:border-0">
                        <p className="text-white text-sm">
                          {new Date(h.practiced_on).toLocaleDateString()}
                          {h.duration_minutes ? ` · ${h.duration_minutes} min` : ''}
                        </p>
                        {h.notes && <p className="text-white/40 text-xs">{h.notes}</p>}
                      </div>
                    ))}
                  </div>
                  <div className="flex flex-col gap-2">
                    <div className="flex gap-2">
                      <input className="input text-sm" type="date"
                             max={new Date().toISOString().slice(0, 10)}
                             value={newPractice.practiced_on}
                             onChange={e => setNewPractice(n => ({ ...n, practiced_on: e.target.value }))} />
                      <input className="input text-sm" type="number" min="1" max="300" placeholder="Minutes"
                             value={newPractice.duration_minutes}
                             onChange={e => setNewPractice(n => ({ ...n, duration_minutes: e.target.value }))} />
                    </div>
                    <input className="input text-sm" placeholder="Notes (optional)"
                           value={newPractice.notes}
                           onChange={e => setNewPractice(n => ({ ...n, notes: e.target.value }))} />
                    <Button onClick={savePracticeLog} disabled={savingPractice} size="sm">
                      {savingPractice ? 'Saving…' : 'Log Practice'}
                    </Button>
                  </div>
                </Card>
              </div>
            )}
          </div>
        )}

        {/* Notes tab */}
        {tab === 'notes' && (
          <div className="flex flex-col gap-4">
            <Card>
              <h3 className="font-semibold text-white mb-3">Add Note</h3>
              <textarea
                className="input resize-none h-24 text-sm mb-3"
                placeholder="Observations, goals, progress notes…"
                value={noteText}
                onChange={e => setNoteText(e.target.value)}
              />
              <Button onClick={saveNote} disabled={savingNote || !noteText.trim()} size="sm">
                {savingNote ? 'Saving…' : 'Save Note'}
              </Button>
            </Card>

            {notes.map(n => (
              <Card key={n.id} className="border-l-2 border-l-brand-teal">
                <p className="text-white text-sm whitespace-pre-wrap">{n.content}</p>
                <p className="text-white/30 text-xs mt-2">{new Date(n.created_at).toLocaleString()}</p>
                {n.tags?.length > 0 && (
                  <div className="flex gap-2 mt-2 flex-wrap">
                    {n.tags.map(t => <span key={t} className="badge bg-brand-teal/20 text-brand-teal">{t}</span>)}
                  </div>
                )}
              </Card>
            ))}

            {notes.length === 0 && (
              <Card className="text-center py-12">
                <FileText size={28} className="text-white/20 mx-auto mb-2" />
                <p className="text-white/40">No notes yet</p>
              </Card>
            )}
          </div>
        )}
      </div>
      </div>
    </div>
  )
}
