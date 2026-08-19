import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Check } from 'lucide-react'
import { Button } from '../components/ui'

// Prices here are illustrative placeholders (Netflix-style tier pricing,
// picked as a starting point) -- billing.py's checkout endpoints are
// still honest 501 stubs (see that file's docstring) until a real
// provider (Stripe/Razorpay) is wired up. plan_type strings match what
// the backend actually creates: "parent_monthly" / "therapist_monthly".
const PLANS = [
  {
    key: 'parent_monthly',
    name: 'Family',
    price: '₹499',
    period: '/month',
    tagline: 'For parents supporting one child at home',
    features: [
      'All 5 games — BreathQuest, Voice Hurdle Race, VaakMirror, Chime, Flashcards',
      'Weekly progress summary, in plain language',
      "Today's difficulty, adapted automatically",
      'Works with or without a therapist',
      '8 languages',
    ],
    cta: 'Start free trial',
    to: '/parent/login?mode=register',
  },
  {
    key: 'therapist_monthly',
    name: 'Professional',
    price: '₹1,499',
    period: '/month',
    tagline: 'For therapists managing a caseload',
    features: [
      'Everything in Family, per patient',
      'Full caseload dashboard across all 5 games',
      'Assignments, goals, and home-practice tracking',
      'PDF progress reports',
      'AI-generated per-patient recommendations',
    ],
    cta: 'Start free trial',
    to: '/therapist/login?mode=register',
  },
]

export default function Pricing() {
  const navigate = useNavigate()
  return (
    <div className="min-h-screen bg-ink relative">
      <div className="max-w-4xl mx-auto px-6 py-12">
        <button onClick={() => navigate('/')}
                className="text-paper/40 hover:text-paper text-sm flex items-center gap-1.5 mb-10 transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" /> Back
        </button>

        <h1 className="font-display text-4xl font-bold text-paper text-center mb-3">
          Simple pricing, real practice.
        </h1>
        <p className="text-paper/50 text-center mb-12">
          Every plan includes a free trial. Cancel anytime.
        </p>

        <div className="grid md:grid-cols-2 gap-6">
          {PLANS.map((plan) => (
            <div key={plan.key} className="rounded-3xl border border-white/10 bg-white/[0.03] p-8 flex flex-col">
              <h2 className="font-display text-xl font-bold text-paper mb-1">{plan.name}</h2>
              <p className="text-paper/40 text-sm mb-6">{plan.tagline}</p>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="font-display text-4xl font-bold text-paper">{plan.price}</span>
                <span className="text-paper/40 text-sm">{plan.period}</span>
              </div>
              <ul className="flex flex-col gap-3 mb-8 flex-1">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-paper/70 text-sm">
                    <Check className="w-4 h-4 text-mint shrink-0 mt-0.5" />
                    {f}
                  </li>
                ))}
              </ul>
              <Button onClick={() => navigate(plan.to)} className="w-full">
                {plan.cta}
              </Button>
            </div>
          ))}
        </div>

        <p className="text-paper/25 text-xs text-center mt-10">
          Prices shown are introductory and may change. See our{' '}
          <button onClick={() => navigate('/terms')} className="underline hover:text-paper/50">Terms</button>{' '}
          and{' '}
          <button onClick={() => navigate('/privacy')} className="underline hover:text-paper/50">Privacy Policy</button>.
        </p>
      </div>
    </div>
  )
}
