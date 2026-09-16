import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { dashboardAPI, patientsAPI, getErrorMessage } from '../../api/client'
import { Card, Badge, Button, PageLoader, Sidebar, AmbientGlow, AboutModal, LevelIcon } from '../../components/ui'
import { ArrowLeft, CloudOff, LayoutDashboard, Settings, Gamepad2, Bell, Waves, Mic, Layers, Stethoscope } from 'lucide-react'
import { SOUNDS } from '../../vaakmirror/data/soundTaxonomy'

const FLASHCARD_PHONEMES = [
  ['B','b'], ['P','p'], ['M','m'], ['D','d'], ['T','t'], ['N','n'], ['G','g'], ['K','k'],
  ['F','f'], ['V','v'], ['S','s'], ['Z','z'], ['SH','sh'], ['CH','ch'], ['JH','j'],
  ['L','l'], ['R','r'], ['W','w'], ['Y','y'], ['H','h'], ['TH','th'],
  ['AE','a (cat)'], ['AO','aw (ball)'], ['EH','e (bed)'], ['IH','i (sit)'],
  ['IY','ee (see)'], ['UW','oo (moon)'], ['RT','retroflex t'], ['RD','retroflex d'],
]

const GAMES = {
  breathquest: {
    label: 'BreathQuest',
    icon: Gamepad2,
    levels: [
      { id: 'balloon', label: 'Balloon' }, { id: 'candle', label: 'Candle' },
      { id: 'dandelion', label: 'Dandelion' }, { id: 'dragon', label: 'Dragon' },
      { id: 'float_rider', label: 'Float Rider' }, { id: 'pinwheel', label: 'Pinwheel' },
    ],
  },
  chime: {
    label: 'Chime',
    icon: Bell,
    levels: [
      { id: 'aa', label: 'Rocket Launch' }, { id: 'oo', label: 'Submarine Dive' },
      { id: 'ma', label: 'Firefly Jar' }, { id: 'fa', label: 'Bubble Garden' },
      { id: 'ha', label: 'Bubble Wrap Pop' }, { id: 'ee', label: 'Xylophone Tower' },
      { id: 'r', label: "Lion's Roar" }, { id: 'village-builder', label: 'Village Builder' },
    ],
  },
  voicehurdlerace: {
    label: 'Voice Hurdle Race',
    icon: Waves,
    levels: [
      { id: 1, label: "Level 1: Blip's Green Plains" },
      { id: 2, label: "Level 2: Zog's Circuit Desert" },
      { id: 3, label: "Level 3: Glorb's Swamp Moon" },
      { id: 4, label: "Level 4: Cosmo's Red Frontier" },
      { id: 5, label: "Level 5: Comet's Starfield" },
    ],
  },
  vaakmirror: {
    label: 'VaakMirror',
    icon: Mic,
    levels: SOUNDS.map(s => ({ id: s.id, label: s.label })),
  },
  flashcards: {
    label: 'Flashcards',
    icon: Layers,
    levels: FLASHCARD_PHONEMES.map(([id, label]) => ({ id, label })),
  },
  // No fixed level list -- unlike the other four games, which phonemes
  // exist for Assessment depends on which words (in which language) this
  // specific child has actually been assessed on. `levels` stays empty
  // here and is populated per-patient below (see assessmentLevels state).
  assessment: {
    label: 'Assessment',
    icon: Stethoscope,
    levels: [],
  },
}

const LADDER_ORDER = ['rule_based', 'tabular_q', 'ppo', 'recurrent_ppo']
const POLICY_INFO = {
  rule_based: {
    label: 'Rule-based', short: 'Using general guidelines',
    detail: "Not enough of this child's own attempts logged yet, so the agent falls back to fixed rules based on typical patterns across children.",
  },
  bandit: {
    label: 'Bandit', short: 'Legacy fallback (retired)',
    detail: 'An older policy type kept only for backward compatibility with historical data — no longer assigned to new sessions.',
  },
  tabular_q: {
    label: 'Tabular Q-learning', short: 'Learned from this child',
    detail: "Has enough of this child's own logged attempts to make personalized calls instead of general guidelines.",
  },
  ppo: {
    label: 'PPO', short: 'Fine-tuned in real time',
    detail: 'A more advanced learner that keeps adapting as new attempts come in.',
  },
  recurrent_ppo: {
    label: 'Recurrent PPO', short: 'Remembers recent patterns',
    detail: 'Like PPO, but also factors in the sequence of recent attempts, not just the latest one.',
  },
}

function RungGlyph({ policyKey, active }) {
  const stroke = active ? '#1D9E75' : 'rgba(255,255,255,0.35)'
  const common = { fill: 'none', stroke, strokeWidth: 2.5, strokeLinecap: 'round' }
  switch (policyKey) {
    case 'rule_based':
      return <svg viewBox="0 0 24 24" className="w-5 h-5"><line x1="4" y1="12" x2="20" y2="12" {...common} /></svg>
    case 'tabular_q':
      return (
        <svg viewBox="0 0 24 24" className="w-5 h-5">
          <line x1="5" y1="18" x2="5" y2="13" {...common} />
          <line x1="12" y1="18" x2="12" y2="9" {...common} />
          <line x1="19" y1="18" x2="19" y2="5" {...common} />
        </svg>
      )
    case 'ppo':
      return (
        <svg viewBox="0 0 24 24" className="w-5 h-5">
          <circle cx="6" cy="6" r="2.3" {...common} />
          <circle cx="18" cy="6" r="2.3" {...common} />
          <circle cx="12" cy="18" r="2.3" {...common} />
          <line x1="8" y1="7" x2="10.5" y2="16" {...common} strokeWidth="2" />
          <line x1="16" y1="7" x2="13.5" y2="16" {...common} strokeWidth="2" />
          <line x1="8" y1="6" x2="16" y2="6" {...common} strokeWidth="2" />
        </svg>
      )
    case 'recurrent_ppo':
      return (
        <svg viewBox="0 0 24 24" className="w-5 h-5">
          <path d="M5 12a7 7 0 1 1 2 5" {...common} />
          <path d="M5 15v-3h3" {...common} />
        </svg>
      )
    default:
      return <svg viewBox="0 0 24 24" className="w-5 h-5"><circle cx="12" cy="12" r="3" {...common} /></svg>
  }
}

function CompactRung({ policyKey, reached, onToggle, isOpen }) {
  const info = POLICY_INFO[policyKey]
  return (
    <div>
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 py-2 text-left group"
      >
        <div className={`flex items-center justify-center w-6 h-6 rounded-full shrink-0 ${
          reached ? 'text-brand-green' : 'text-white/20'
        }`}>
          <RungGlyph policyKey={policyKey} active={reached} />
        </div>
        <span className={`text-sm ${reached ? 'text-white/55' : 'text-white/30'} group-hover:text-white/70 transition`}>
          {info.label}
        </span>
        <span className={`text-xs ml-auto ${reached ? 'text-white/30' : 'text-white/15'}`}>
          {reached ? 'Reached' : 'Not yet'}
        </span>
      </button>
      {isOpen && <p className="text-xs text-white/35 pl-9 pb-2 pr-1">{info.detail}</p>}
    </div>
  )
}

function PolicyLadder({ current, downgradeReason }) {
  const [openInfo, setOpenInfo] = useState(null)
  const currentIdx = LADDER_ORDER.indexOf(current)
  const isRetired = !LADDER_ORDER.includes(current)
  const activeInfo = POLICY_INFO[current]

  return (
    <Card>
      <h3 className="font-semibold text-white mb-1">Where this child's agent is at</h3>
      <p className="text-white/40 text-xs mb-4">
        The stage below is what's active now. Tap any other stage to see what it means.
      </p>

      {/* The active stage gets the only full card treatment on the ladder. */}
      <div className={`rounded-2xl p-4 border ${
        isRetired ? 'bg-brand-amber/[0.08] border-brand-amber/30' : 'bg-brand-green/[0.08] border-brand-green/40'
      }`}>
        <div className="flex items-center gap-3">
          <div className={`flex items-center justify-center w-10 h-10 rounded-full shrink-0 ${
            isRetired ? 'bg-brand-amber text-black' : 'bg-brand-green text-black'
          }`}>
            <RungGlyph policyKey={current} active />
          </div>
          <div className="flex-1">
            <span className="font-medium block text-white">{activeInfo?.label || current}</span>
            <p className="text-sm mt-0.5 text-white/70">{activeInfo?.short || 'Not on the usual ladder'}</p>
          </div>
          <Badge color={isRetired ? 'amber' : 'green'}>Active</Badge>
        </div>
        <p className="text-xs text-white/40 mt-2 pl-[52px]">
          {activeInfo?.detail || "This policy isn't part of the normal progression."}
        </p>
      </div>

      {/* Every other stage recedes to a single quiet row -- no card, no border. */}
      {!isRetired && (
        <div className="mt-2 divide-y divide-white/[0.06]">
          {LADDER_ORDER.filter(key => key !== current).map(key => (
            <CompactRung
              key={key}
              policyKey={key}
              reached={LADDER_ORDER.indexOf(key) < currentIdx}
              isOpen={openInfo === key}
              onToggle={() => setOpenInfo(openInfo === key ? null : key)}
            />
          ))}
        </div>
      )}

      {downgradeReason && (
        <p className="text-white/40 text-xs mt-4 border-t border-white/10 pt-3">{downgradeReason}</p>
      )}
    </Card>
  )
}

function GameSelector({ game, onSelect }) {
  return (
    <div className="mb-4 -mx-6 px-6 border-b border-white/10">
      <div className="flex gap-5 overflow-x-auto no-scrollbar">
        {Object.entries(GAMES).map(([key, g]) => {
          const GameIcon = g.icon
          const isActive = key === game
          return (
            <button
              key={key}
              onClick={() => onSelect(key)}
              className={`flex items-center gap-1.5 pb-3 pt-1 border-b-2 text-sm whitespace-nowrap shrink-0 transition ${
                isActive
                  ? 'border-brand-green text-white font-medium'
                  : 'border-transparent text-white/40 hover:text-white/65'
              }`}
            >
              <GameIcon size={15} />
              {g.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function LevelStrip({ game, levelId, levels, onSelect }) {
  return (
    <div className="mb-6 -mx-6 px-6">
      <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
        {levels.map(l => {
          const isActive = l.id === levelId
          return (
            <button
              key={l.id}
              onClick={() => onSelect(l.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm whitespace-nowrap shrink-0 transition ${
                isActive ? 'bg-brand-green text-black font-medium' : 'bg-white/5 text-white/50 hover:bg-white/10'
              }`}
            >
              {game === 'breathquest' && <LevelIcon id={l.id} className="w-4 h-4" />}
              {l.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function AgentInsight() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { therapist, logout } = useAuth()
  const [searchParams] = useSearchParams()
  const requestedGame = searchParams.get('game')
  const initialGame = GAMES[requestedGame] ? requestedGame : 'breathquest'
  const [game, setGame] = useState(initialGame)
  const [levelId, setLevelId] = useState(GAMES[initialGame].levels[0]?.id ?? null)
  const [assessmentId, setAssessmentId] = useState(null)
  const [assessmentLevels, setAssessmentLevels] = useState([])
  const [assessmentLevelsLoading, setAssessmentLevelsLoading] = useState(false)
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showTechDetail, setShowTechDetail] = useState(false)

  // Assessment's levels aren't known until we've fetched which phonemes
  // this specific child has actually been assessed on -- every other game
  // has a fixed list to pick a first id from synchronously.
  const currentLevels = game === 'assessment' ? assessmentLevels : GAMES[game].levels

  const selectGame = (g) => {
    setGame(g)
    setLevelId(g === 'assessment' ? null : GAMES[g].levels[0].id)
  }

  // Fetch Assessment's per-patient phoneme list once assessmentId resolves
  // and whenever the child switches into the Assessment tab. GAMES.assessment
  // .levels intentionally stays [] (see its comment above) -- this is the
  // real source.
  useEffect(() => {
    if (game !== 'assessment' || !assessmentId) return
    setAssessmentLevelsLoading(true)
    setError(null)
    dashboardAPI.assessmentAgentLevels(assessmentId)
      .then(r => {
        const levels = (r.data.phonemes || []).map(p => ({ id: p, label: p.toUpperCase() }))
        setAssessmentLevels(levels)
        setLevelId(levels[0]?.id ?? null)
        if (levels.length === 0) {
          setLoading(false)
          setError('This child has no logged Assessment attempts yet, so there\u2019s nothing for the agent to show.')
        }
      })
      .catch(e => {
        setError(getErrorMessage(e, 'Could not load Assessment phoneme levels'))
        setLoading(false)
      })
      .finally(() => setAssessmentLevelsLoading(false))
  }, [game, assessmentId])

  // Agent-status routes (chime.py, breath_agent.py, voicehurdlerace.py) key
  // off Patient.assessment_patient_id, not breathquest_patients.id — but
  // the route param `id` here is the bq_id (that's what the patient list /
  // PatientDetail link passes). Resolve the real assessment id once, from
  // the patient record itself, rather than assuming the two ids match.
  useEffect(() => {
    setAssessmentId(null)
    setError(null)
    patientsAPI.get(id)
      .then(r => {
        if (!r.data.assessment_patient_id) {
          setError('This child has no linked assessment record, so agent status isn\u2019t available yet.')
          setLoading(false)
          return
        }
        setAssessmentId(r.data.assessment_patient_id)
      })
      .catch(e => {
        setError(getErrorMessage(e, 'Could not load this patient'))
        setLoading(false)
      })
  }, [id])

  const load = useCallback(() => {
    if (!assessmentId || !levelId) return
    setLoading(true)
    setError(null)
    dashboardAPI.agentStatus(assessmentId, levelId, 'tabular_q', game)
      .then(r => setStatus(r.data))
      .catch(e => setError(getErrorMessage(e, 'Could not load agent status')))
      .finally(() => setLoading(false))
  }, [assessmentId, levelId, game])

  useEffect(() => { load() }, [load])

  return (
    <div className="min-h-dvh relative flex"
         style={{ background: 'radial-gradient(ellipse 1400px 800px at 15% -10%, #1D9E75 0%, #16332D 35%, #12122A 70%)' }}>
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

      <div className="relative flex-1 min-w-0 max-w-3xl mx-auto px-6 py-8">
        <Button variant="ghost" onClick={() => navigate(`/therapist/patients/${id}`)} className="mb-4">
          <ArrowLeft size={16} className="mr-1" /> Back to patient
        </Button>

        <h1 className="text-xl font-display font-bold text-white mb-1">What the agent sees</h1>
        <p className="text-white/40 text-sm mb-6">
          Read-only — this does not affect gameplay or training data.
        </p>

        <GameSelector game={game} onSelect={selectGame} />
        {currentLevels.length > 0 && (
          <LevelStrip game={game} levelId={levelId} levels={currentLevels} onSelect={setLevelId} />
        )}

        {(loading || assessmentLevelsLoading) ? <PageLoader /> : error ? (
          <Card className="text-center py-16 px-8">
            <div className="w-14 h-14 rounded-2xl bg-brand-coral/10 flex items-center justify-center mx-auto mb-4">
              <CloudOff size={24} className="text-brand-coral" />
            </div>
            <p className="text-white/70 font-medium mb-1">Couldn't load agent status</p>
            <p className="text-white/40 text-sm mb-5 max-w-xs mx-auto">{error}</p>
            <Button onClick={load}>Try again</Button>
          </Card>
        ) : !status ? null : (
          <div className="flex flex-col gap-4">
            <PolicyLadder current={status.policy} downgradeReason={status.downgrade_reason} />

            <Card>
              <div className="flex items-center justify-between mb-1">
                <h3 className="font-semibold text-white">What the agent is looking at</h3>
                <button
                  onClick={() => setShowTechDetail(v => !v)}
                  className="text-xs text-white/40 underline hover:text-white/60"
                >
                  {showTechDetail ? 'Hide technical details' : 'Show technical details'}
                </button>
              </div>
              <p className="text-white/30 text-xs mb-3">
                Based on {status.n_events_considered} recent attempts on this level.
              </p>
              {showTechDetail && (
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-white/30 text-xs">Success rate</p>
                    <p className="text-white">{(status.obs.success_rate * 100).toFixed(0)}%</p>
                  </div>
                  <div>
                    <p className="text-white/30 text-xs">Difficulty</p>
                    <p className="text-white">{(status.obs.difficulty * 100).toFixed(0)}%</p>
                  </div>
                  <div>
                    <p className="text-white/30 text-xs">Frustration</p>
                    <p className="text-white">{(status.obs.frustration * 100).toFixed(0)}%</p>
                  </div>
                  <div>
                    <p className="text-white/30 text-xs">Severity</p>
                    <p className="text-white">{status.obs.severity_numeric.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-white/30 text-xs">Targeted sound</p>
                    <p className="text-white">{status.obs.is_targeted_sound ? 'Yes' : 'No'}</p>
                  </div>
                </div>
              )}
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}
