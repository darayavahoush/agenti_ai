import { useNavigate } from 'react-router-dom'
import { Brain, Play, Wind, Bell, Waves, Layers } from 'lucide-react'
import { Card } from '../ui'

// One accent + icon per game family, matching each family's own home screen.
const FAMILY = {
  Chime:       { color: '#F4B942', Icon: Bell },
  Orpheus:     { color: '#2FB8A6', Icon: Waves },
  Flashcards:  { color: '#A78BFA', Icon: Layers },
  BreathQuest: { color: '#A8FF6F', Icon: Wind },
}

const CONFIDENCE_NOTE = {
  low: 'Based on just a few words, so this is a first guess. Say a few more words for a sharper plan.',
  medium: 'Based on a handful of words. A few more will make it even more accurate.',
}

// "Your game plan": the game-prediction agent's answer for the words the kid
// just said (GET /assessment/me/game-plan, or router state right after
// finishing). Renders nothing when there is no plan, so an assessment with
// no clearly tricky sound doesn't show an empty card.
export default function GamePlanCard({ plan, className = '' }) {
  const navigate = useNavigate()
  if (!plan || !Array.isArray(plan.plan) || plan.plan.length === 0) return null

  return (
    <Card className={`text-left ${className}`}>
      <div className="flex items-center gap-2 mb-1">
        <Brain className="w-4 h-4 text-brand-green" />
        <span className="text-white font-semibold text-sm">Your game plan</span>
      </div>
      {plan.headline && <p className="text-white/60 text-sm mb-4">{plan.headline}</p>}

      <ol className="flex flex-col gap-2.5">
        {plan.plan.map((g) => {
          const fam = FAMILY[g.family] || FAMILY.Chime
          const { Icon } = fam
          return (
            <li
              key={g.id}
              className="rounded-xl border border-white/10 bg-white/[0.04] p-3.5 flex items-start gap-3"
              style={{ borderLeft: `3px solid ${fam.color}` }}
            >
              <div
                className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold"
                style={{ backgroundColor: `${fam.color}22`, color: fam.color }}
                aria-hidden="true"
              >
                {g.priority === 1 ? <Icon size={18} /> : g.priority}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-white font-semibold text-sm leading-tight">
                  {g.name}
                  <span className="text-white/35 font-normal"> · {g.family}</span>
                </p>
                <p className="text-white/55 text-[13px] leading-snug mt-1">{g.reason}</p>
              </div>
              <button
                type="button"
                onClick={() => navigate(g.path)}
                className="shrink-0 self-center inline-flex items-center gap-1 min-h-[40px] px-3 rounded-lg
                           text-xs font-semibold text-brand-dark transition-transform active:scale-95"
                style={{ backgroundColor: fam.color }}
                aria-label={`Play ${g.name}`}
              >
                <Play size={12} /> Play
              </button>
            </li>
          )
        })}
      </ol>

      {CONFIDENCE_NOTE[plan.confidence] && (
        <p className="text-white/35 text-xs mt-3">{CONFIDENCE_NOTE[plan.confidence]}</p>
      )}
    </Card>
  )
}
