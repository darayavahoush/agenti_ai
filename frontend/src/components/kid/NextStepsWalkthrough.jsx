import { useNavigate } from 'react-router-dom'
import { Keyboard, Gamepad2, LineChart, Users, ArrowRight, Sparkles } from 'lucide-react'
import { Card } from '../ui'

// Turns "here's what the assessment found" into "here's exactly what to
// tap next, and why" -- a full walkthrough of the app rather than just a
// list of recommended games (that's GamePlanCard, rendered separately;
// this sits below it and covers everything else the assessment should
// steer a kid toward: Sound Check if it hasn't been done yet, the game
// plan's runner-up games, the progress tracker, and a nudge for the
// grown-up side).
//
// Every step is conditional on real state (alphabetCompleted, whether a
// game plan exists) rather than always showing the same five steps --
// a kid who already did Sound Check and has no clear weak sound shouldn't
// be told to do either.
export default function NextStepsWalkthrough({ plan, alphabetCompleted, severity, firstName, className = '' }) {
  const navigate = useNavigate()
  const name = firstName || 'you'

  const steps = []

  // Runner-up games from the plan beyond the single top pick GamePlanCard
  // already highlights -- surfaced here as "then try" so the walkthrough
  // doesn't just repeat that card verbatim.
  const rest = (plan?.plan || []).slice(1, 3)
  if (rest.length > 0) {
    steps.push({
      icon: Gamepad2,
      color: '#A78BFA',
      title: 'Then try these too',
      body: `Once ${name === 'you' ? "you've" : `${name}'s`} warmed up, these round out the practice:`,
      list: rest.map((g) => ({ label: g.name, sub: g.family, path: g.path })),
    })
  }

  if (!alphabetCompleted) {
    steps.push({
      icon: Keyboard,
      color: '#F59E0B',
      title: 'Try Sound Check',
      body: "Tap a letter, see how your mouth is supposed to make it, then say it out loud. It's a quick way to spot exactly which sounds need work -- and it fine-tunes the mirror games too.",
      action: { label: 'Open Sound Check', onClick: () => navigate('/assessment') },
    })
  }

  steps.push({
    icon: LineChart,
    color: '#2FB8A6',
    title: 'Keep an eye on progress',
    body: 'Every game session gets logged here -- accuracy over time, streaks, and what to practice next.',
    action: { label: 'View my progress', onClick: () => navigate('/play/progress') },
  })

  steps.push({
    icon: Users,
    color: '#60A5FA',
    title: 'Loop in a grown-up',
    body: 'A parent or therapist watching this account can see this same report, set goals, and plan practice time together -- worth pointing them to the Progress page too.',
  })

  if (steps.length === 0) return null

  return (
    <Card className={`text-left ${className}`}>
      <div className="flex items-center gap-2 mb-1">
        <Sparkles className="w-4 h-4 text-brand-green" />
        <span className="text-white font-semibold text-sm">Your walkthrough</span>
      </div>
      <p className="text-white/60 text-sm mb-4">
        {severity
          ? "Here's exactly where to go next, based on today's check-in."
          : "Here's where to go next in the app."}
      </p>

      <ol className="flex flex-col gap-0">
        {steps.map((step, i) => {
          const { icon: Icon } = step
          const isLast = i === steps.length - 1
          return (
            <li key={step.title} className="relative pl-11 pb-5 last:pb-0">
              {!isLast && (
                <span
                  className="absolute left-[15px] top-8 bottom-0 w-px bg-white/10"
                  aria-hidden="true"
                />
              )}
              <div
                className="absolute left-0 top-0 w-8 h-8 rounded-full flex items-center justify-center shrink-0"
                style={{ backgroundColor: `${step.color}22`, color: step.color }}
                aria-hidden="true"
              >
                <Icon size={15} />
              </div>

              <p className="text-white font-semibold text-sm leading-tight mb-1">{step.title}</p>
              <p className="text-white/55 text-[13px] leading-snug mb-2">{step.body}</p>

              {step.list && (
                <div className="flex flex-col gap-1.5 mb-2">
                  {step.list.map((g) => (
                    <button
                      key={g.path}
                      type="button"
                      onClick={() => navigate(g.path)}
                      className="flex items-center justify-between gap-2 text-left rounded-lg
                                 border border-white/10 bg-white/[0.03] px-3 py-2 min-h-[40px]
                                 hover:bg-white/[0.06] transition-colors"
                    >
                      <span className="text-white/80 text-xs font-medium">
                        {g.label} <span className="text-white/35 font-normal">· {g.sub}</span>
                      </span>
                      <ArrowRight size={13} className="text-white/40 shrink-0" />
                    </button>
                  ))}
                </div>
              )}

              {step.action && (
                <button
                  type="button"
                  onClick={step.action.onClick}
                  className="inline-flex items-center gap-1 min-h-[36px] px-3 rounded-lg text-xs font-semibold
                             transition-transform active:scale-95"
                  style={{ backgroundColor: `${step.color}22`, color: step.color }}
                >
                  {step.action.label} <ArrowRight size={12} />
                </button>
              )}
            </li>
          )
        })}
      </ol>
    </Card>
  )
}
