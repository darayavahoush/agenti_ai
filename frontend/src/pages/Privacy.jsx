import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ShieldCheck, Database, Users, CreditCard, Trash2, Mail } from 'lucide-react'

// Content reflects what this app actually does today, not generic
// boilerplate: COPPA-gated parental consent for kid accounts (see
// backend/app/breathquest_core/parental_consent.py), no live payment
// provider yet (billing.py is a 501 stub), no ad tracking or
// third-party ad sharing anywhere in the codebase.
const SECTIONS = [
  {
    title: 'What we collect',
    icon: Database,
    badgeClass: 'bg-sky/15 border-sky/25 text-sky-light',
    body: `For kids: a first name, an avatar choice, and gameplay data (session
    scores, breath/voice metrics, phoneme accuracy). For parents and
    therapists: an email, password, and optional phone number. A parent's
    email and phone are used specifically to verify parental consent
    before any child account is created.`,
  },
  {
    title: "Children's privacy (COPPA)",
    icon: ShieldCheck,
    badgeClass: 'bg-mint/15 border-mint/25 text-mint-light',
    body: `A child account can only be created after a parent's email and phone
    number are verified. We collect the minimum needed to run the games
    and show progress — no behavioral advertising, no data sale, no
    tracking outside this app.`,
  },
  {
    title: 'Who can see a child\'s data',
    icon: Users,
    badgeClass: 'bg-coral/15 border-coral/25 text-coral-light',
    body: `Only the linked parent account and, if one exists, the assigned
    therapist. A parent can delete their account at any time, which
    deletes their child's account and all associated game data.`,
  },
  {
    title: 'Payment information',
    icon: CreditCard,
    badgeClass: 'bg-ember/15 border-ember/25 text-ember-glow',
    body: `We do not yet process live payments — checkout is not currently
    connected to a payment provider. When it is, this section will be
    updated with the provider's name and how card data is handled (we
    never store raw card numbers ourselves).`,
  },
  {
    title: 'Data deletion',
    icon: Trash2,
    badgeClass: 'bg-sky/15 border-sky/25 text-sky-light',
    body: `Any account holder can permanently delete their account and data
    from their account settings. Parent deletion cascades to the linked
    child's account. This is irreversible.`,
  },
  {
    title: 'Contact',
    icon: Mail,
    badgeClass: 'bg-mint/15 border-mint/25 text-mint-light',
    body: `Questions about this policy or a request to access, correct, or
    delete data can be sent to the contact address on your account's
    settings page.`,
  },
]

export default function Privacy() {
  const navigate = useNavigate()
  return (
    <div className="min-h-screen bg-ink">
      <div className="max-w-2xl mx-auto px-6 py-12">
        <button onClick={() => navigate(-1)}
                className="text-paper/40 hover:text-paper text-sm flex items-center gap-1.5 mb-10 transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" /> Back
        </button>

        <div className="w-14 h-14 rounded-2xl bg-mint/15 border border-mint/25 flex items-center justify-center mb-5">
          <ShieldCheck className="w-7 h-7 text-mint-light" />
        </div>
        <h1 className="font-display text-3xl font-bold text-paper mb-2">Privacy Policy</h1>
        <p className="text-paper/40 text-sm mb-10">Last updated August 2026</p>

        <div className="flex flex-col gap-4">
          {SECTIONS.map((s) => {
            const Icon = s.icon
            return (
              <div key={s.title} className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className={`w-9 h-9 rounded-xl border flex items-center justify-center shrink-0 ${s.badgeClass}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <h2 className="text-paper font-semibold">{s.title}</h2>
                </div>
                <p className="text-paper/60 text-sm leading-relaxed whitespace-pre-line">{s.body}</p>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
