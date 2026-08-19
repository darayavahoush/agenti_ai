import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

const SECTIONS = [
  {
    title: 'What this is',
    body: `This app provides speech-practice games and progress tracking for
    children, alongside dashboards for parents and therapists. It is a
    practice and progress-tracking tool, not a substitute for professional
    speech-language therapy or medical advice.`,
  },
  {
    title: 'Accounts',
    body: `A child account requires a parent's verified consent. A parent or
    therapist account requires a valid email and password. You're
    responsible for keeping your login credentials, including a child's
    PIN, private.`,
  },
  {
    title: 'Subscriptions and trials',
    body: `Plans shown on our pricing page include a free trial. Pricing is
    introductory and may change; we'll notify you before any change takes
    effect for an existing subscription. Live payment processing is not
    yet active — no charge occurs until it is.`,
  },
  {
    title: 'Account deletion',
    body: `You may delete your account at any time from your account settings.
    Deletion is permanent and cannot be undone. A parent deleting their
    account also deletes their linked child's account and all game data.`,
  },
  {
    title: 'Acceptable use',
    body: `Accounts are for the named user only. Don't use this app to collect
    or share data about a child beyond what's needed for their own
    practice and progress tracking.`,
  },
  {
    title: 'Changes to these terms',
    body: `We may update these terms as the product changes. Continued use
    after an update means you accept the revised terms.`,
  },
]

export default function Terms() {
  const navigate = useNavigate()
  return (
    <div className="min-h-screen bg-ink">
      <div className="max-w-2xl mx-auto px-6 py-12">
        <button onClick={() => navigate(-1)}
                className="text-paper/40 hover:text-paper text-sm flex items-center gap-1.5 mb-10 transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" /> Back
        </button>
        <h1 className="font-display text-3xl font-bold text-paper mb-2">Terms of Service</h1>
        <p className="text-paper/40 text-sm mb-10">Last updated August 2026</p>
        <div className="flex flex-col gap-8">
          {SECTIONS.map((s) => (
            <div key={s.title}>
              <h2 className="text-paper font-semibold mb-2">{s.title}</h2>
              <p className="text-paper/60 text-sm leading-relaxed whitespace-pre-line">{s.body}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
