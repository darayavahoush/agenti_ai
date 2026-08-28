import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { KeyRound, PartyPopper, Sparkles, ArrowRight, ArrowLeft, Volume2, Stethoscope, Mail, Phone } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { authAPI, verifyAPI, getErrorMessage } from '../../api/client'
import { Button, Avatar } from '../../components/ui'
import { Creature } from '../../components/ui/Creatures'
import { speak } from '../../lib/speech'

const AVATARS = ['chick', 'dragon', 'bunny', 'fox', 'rocket', 'fish']
const AVATAR_NAMES = { chick: 'Chicky', dragon: 'Dino', bunny: 'Hoppy', fox: 'Foxy', rocket: 'Zoom', fish: 'Finley' }

// Same four worlds GamePicker.jsx lists post-login, plus a 5th badge for the
// assessment feature (not a "world" -- a diagnostic tool -- so it gets its
// own higher-energy copy instead of reusing GamePicker text).
const GAMES = [
  { key: 'breathquest', emoji: '🐉', name: 'BreathQuest', desc: 'Breath-controlled adventures — 6 levels',
    badgeClass: 'bg-ember/15 text-ember-glow border-ember/25' },
  { key: 'orpheus', emoji: '🪞', name: 'Orpheus', desc: 'Mouth & tongue mirror games — 3 games',
    badgeClass: 'bg-mint/15 text-mint-light border-mint/25' },
  { key: 'chime', emoji: '🔔', name: 'Chime', desc: 'Say the word, build a village',
    badgeClass: 'bg-coral/15 text-coral-light border-coral/25' },
  { key: 'voice-hurdle-race', emoji: '🐶', name: 'Voice Hurdle Race', desc: 'Use your voice to jump hurdles',
    badgeClass: 'bg-sky/15 text-sky-light border-sky/25' },
  { key: 'assessment', emoji: '⚡', name: 'Speech Assessment', desc: 'Real-time AI voice analysis — your progress, scored instantly',
    badgeClass: 'bg-white/10 text-white/90 border-white/25' },
]

// Same dusk-into-ember gradient Landing.jsx uses one screen back — this page
// used to drop straight from that illustrated world into a flat navy square,
// which is most of why it read as cold. Carrying the gradient (and a little
// of the ember glow) through makes the whole kid flow feel like one place.
const BG = {
  background: 'linear-gradient(180deg, #12142E 0%, #241F49 45%, #3A2C5C 100%)',
}

const EMBERS = [
  { left: '15%', delay: '0s',   duration: '12s', size: 4 },
  { left: '82%', delay: '3s',   duration: '14s', size: 3 },
  { left: '50%', delay: '6s',   duration: '11s', size: 4 },
]

// Small inline "hear it again" affordance, reused across every spoken
// screen in this file so the tap target and icon are consistent.
function SpeakButton({ onClick, className = 'text-white/25 hover:text-white/50' }) {
  return (
    <button onClick={onClick} className={`inline-flex transition-colors ${className}`} aria-label="Hear this again">
      <Volume2 className="w-3.5 h-3.5" />
    </button>
  )
}

// A little welcome crew instead of a lone floating game-controller emoji —
// this is the first thing a kid sees after tapping "I'm a Kid!" on Landing,
// so it's the moment to introduce the cast, not a generic icon.
function WelcomeCrew() {
  return (
    <div className="relative flex items-end justify-center gap-4 mt-12 mb-3">
      <div className="absolute inset-x-10 inset-y-0 rounded-full bg-ember/20 blur-2xl motion-safe:animate-pulse-slow" />
      <div className="relative w-14 h-14 motion-safe:animate-float"
           style={{ animationDelay: '0.4s', animationDuration: '3.4s' }}>
        <Creature species="bunny" className="w-full h-full drop-shadow-lg" />
      </div>
      <div className="relative w-20 h-20 mb-2 motion-safe:animate-float"
           style={{ animationDelay: '0s', animationDuration: '3s' }}>
        <Creature species="chick" className="w-full h-full drop-shadow-xl" />
      </div>
      <div className="relative w-14 h-14 motion-safe:animate-float"
           style={{ animationDelay: '0.9s', animationDuration: '3.8s' }}>
        <Creature species="fox" className="w-full h-full drop-shadow-lg" />
      </div>
    </div>
  )
}

// The gradient-bordered glass panel Landing.jsx's three big buttons use,
// pulled out so register/login get the same warm treatment instead of a
// flat bg-brand-card square that looks pasted in from a different app.
const GLASS_ACCENTS = {
  'brand-green': { border: 'rgba(168,255,111,0.35)', glow: 'rgba(168,255,111,0.12)' },
  'brand-amber': { border: 'rgba(250,199,117,0.35)', glow: 'rgba(250,199,117,0.12)' },
}

function GlassPanel({ children, accent = 'brand-green', className = '' }) {
  const a = GLASS_ACCENTS[accent] || GLASS_ACCENTS['brand-green']
  return (
    <div
      className={`relative overflow-hidden rounded-[2rem] p-7 border-2 backdrop-blur-sm
                  bg-gradient-to-br from-white/[0.06] to-transparent ${className}`}
      style={{ borderColor: a.border }}
    >
      <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full blur-3xl" style={{ backgroundColor: a.glow }} />
      <div className="relative">{children}</div>
    </div>
  )
}

function PinDots({ length }) {
  return (
    <div className="flex justify-center gap-3 mb-4">
      {[0, 1, 2, 3].map(i => (
        <div key={i} className={`w-5 h-5 rounded-full border-2 transition-all
          ${length > i ? 'bg-brand-green border-brand-green' : 'border-white/30'}`} />
      ))}
    </div>
  )
}

function PinPad({ onDigit, onDelete }) {
  return (
    <div className="grid grid-cols-3 gap-2 mb-4">
      {[1, 2, 3, 4, 5, 6, 7, 8, 9, '', 0, '⌫'].map((d, i) => (
        <button key={i}
          onClick={() => d === '⌫' ? onDelete() : d !== '' ? onDigit(String(d)) : null}
          disabled={d === ''}
          aria-label={d === '⌫' ? 'Delete digit' : d === '' ? undefined : `Digit ${d}`}
          className={`h-14 rounded-xl font-vm-display text-xl font-bold transition-all active:scale-95
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70
            ${d === '' ? 'invisible' : d === '⌫' ? 'bg-white/5 text-white/50 hover:bg-white/10'
              : 'bg-white/10 text-white hover:bg-brand-green/20 hover:text-brand-green'}`}>
          {d}
        </button>
      ))}
    </div>
  )
}

export default function KidPlay() {
  const [mode, setMode]         = useState('choose')   // choose | register | login
  const [avatar, setAvatar]     = useState('chick')
  const [firstName, setFirstName] = useState('')
  const [playerCode, setPlayerCode] = useState('')
  const [pin, setPin]           = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const [registered, setRegistered] = useState(null)  // {player_code, first_name}
  // COPPA: New Player signup can't create an account without a parent's
  // email and phone (both required, see parental_consent.py). 'form'
  // collects the kid's own details first so a parent isn't asked for
  // contact info before there's even an account to consent to.
  // TEMPORARY 2026-08-12: no OTP round-trip right now -- 'parentContact'
  // registers immediately once both fields are filled in. See
  // handleFinishRegistration's comment.
  const [registerStep, setRegisterStep] = useState('form')  // form | parentContact | verifyEmail | verifyPhone
  const [parentEmail, setParentEmail]   = useState('')
  const [parentPhone, setParentPhone]   = useState('')
  const [emailCode, setEmailCode]       = useState('')
  const [phoneCode, setPhoneCode]       = useState('')
  const [resendMsg, setResendMsg]       = useState('')
  const [mounted, setMounted]   = useState(false)
  const [activeGame, setActiveGame] = useState(null)  // key of the badge tapped for a quick info popover, or null
  const [candidates, setCandidates]               = useState([])
  const [candidatesLoading, setCandidatesLoading] = useState(false)
  const [candidatesError, setCandidatesError]     = useState('')
  const [selectedPatientId, setSelectedPatientId] = useState('')
  const { loginKid, registerKid, setupKidPin } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 30)
    return () => clearTimeout(t)
  }, [])

  const fetchCandidates = () => {
    setCandidatesLoading(true)
    setCandidatesError('')
    authAPI.kidCandidates()
      .then(({ data }) => setCandidates(data.patients || []))
      .catch(e => setCandidatesError(getErrorMessage(e)))
      .finally(() => setCandidatesLoading(false))
  }

  useEffect(() => {
    if (mode !== 'assessment' || candidates.length > 0 || candidatesLoading) return
    fetchCandidates()
  }, [mode])

  // Verbal instructions on this screen are manual, tap-to-hear only — no
  // auto-play. Auto-speaking every time a kid lands on a nav/login screen
  // got flagged as an annoying voice-over; that judgment call only applies
  // here (and Landing.jsx / GamePicker.jsx) — the actual games still
  // auto-speak once per level/attempt via useSpokenInstruction, since
  // that's instructional, not just narration of a menu.
  const CHOOSE_TXT     = 'Ready to play? Tap New Player to create an account, or I have a code to log back in.'
  const REGISTER_TXT   = 'Create your account. Type your name, pick your character, and choose a 4 digit PIN.'
  const LOGIN_TXT      = 'Welcome back! Enter your name or player code, and your PIN.'
  const ASSESSMENT_TXT = 'Find your name in the list, pick your character, and choose a 4 digit PIN.'
  const registeredText = registered
    ? `You're in, ${AVATAR_NAMES[avatar]}! Write down your player code and your PIN so you can log back in.`
    : null
  const replayChoose     = () => speak(CHOOSE_TXT)
  const replayRegister   = () => speak(REGISTER_TXT)
  const replayLogin      = () => speak(LOGIN_TXT)
  const replayAssessment = () => speak(ASSESSMENT_TXT)
  const replayRegistered = () => { if (registeredText) speak(registeredText) }

  const handlePin = (digit) => { if (pin.length < 4) setPin(p => p + digit) }
  const deletePin = () => setPin(p => p.slice(0, -1))

  const handleContinueToParentContact = () => {
    if (!firstName.trim()) { setError('What should we call you?'); return }
    if (pin.length < 4)    { setError('Choose a 4-digit PIN'); return }
    setError(''); setRegisterStep('parentContact')
  }

  // Step 1: parent fills in email + phone -> send the email code.
  const handleSendParentContact = async () => {
    if (!parentEmail.trim()) { setError("Enter a parent's email"); return }
    if (!parentPhone.trim()) { setError("Enter a parent's phone number"); return }
    setError(''); setResendMsg(''); setLoading(true)
    try {
      await verifyAPI.request({ email: parentEmail.trim() })
      setRegisterStep('verifyEmail')
    } catch (e) {
      setError(getErrorMessage(e, "Couldn't send the verification code — try again"))
    } finally {
      setLoading(false)
    }
  }

  const handleResendEmailCode = async () => {
    setError(''); setResendMsg(''); setLoading(true)
    try {
      await verifyAPI.request({ email: parentEmail.trim() })
      setResendMsg('Code resent!')
    } catch (e) {
      setError(getErrorMessage(e, "Couldn't resend the code — try again"))
    } finally {
      setLoading(false)
    }
  }

  // Step 2: parent enters the emailed code -> confirm it, then
  // immediately kick off the phone code so there's no extra tap.
  const handleConfirmEmailCode = async () => {
    if (emailCode.trim().length !== 6) { setError('Enter the 6-digit code'); return }
    setError(''); setLoading(true)
    try {
      await verifyAPI.confirm({ email: parentEmail.trim(), code: emailCode.trim() })
      await verifyAPI.phoneRequest({ phone: parentPhone.trim() })
      setPhoneCode(''); setResendMsg('')
      setRegisterStep('verifyPhone')
    } catch (e) {
      setError(getErrorMessage(e, "That code didn't work — try again"))
    } finally {
      setLoading(false)
    }
  }

  const handleResendPhoneCode = async () => {
    setError(''); setResendMsg(''); setLoading(true)
    try {
      await verifyAPI.phoneRequest({ phone: parentPhone.trim() })
      setResendMsg('Code resent!')
    } catch (e) {
      setError(getErrorMessage(e, "Couldn't resend the code — try again"))
    } finally {
      setLoading(false)
    }
  }

  // Step 3: parent enters the texted code -> confirm it, then
  // finally create the account.
  const handleConfirmPhoneCode = async () => {
    if (phoneCode.trim().length !== 6) { setError('Enter the 6-digit code'); return }
    setError(''); setLoading(true)
    try {
      await verifyAPI.phoneConfirm({ phone: parentPhone.trim(), code: phoneCode.trim() })
    } catch (e) {
      setError(getErrorMessage(e, "That code didn't work — try again"))
      setLoading(false)
      return
    }
    await handleFinishRegistration()
  }

  const handleFinishRegistration = async () => {
    setError(''); setLoading(true)
    try {
      const data = await registerKid(firstName.trim(), avatar, pin, parentEmail.trim(), parentPhone.trim())
      setRegistered({ player_code: data.player_code, first_name: data.first_name })
    } catch (e) {
      setError(getErrorMessage(e, "Couldn't create the account — try again"))
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = async () => {
    if (!playerCode.trim()) { setError('Enter your name or player code'); return }
    if (pin.length < 4)     { setError('Enter your PIN'); return }
    setError(''); setLoading(true)
    try {
      await loginKid(playerCode.trim().toUpperCase(), pin)
      navigate('/play/levels')
    } catch (e) {
      setError(getErrorMessage(e, 'Wrong code or PIN — try again!'))
      setPin('')
    } finally {
      setLoading(false)
    }
  }

  const handleAssessmentSetup = async () => {
    if (pin.length < 4) { setError('Choose a 4-digit PIN'); return }
    setError(''); setLoading(true)
    try {
      await setupKidPin(selectedPatientId, avatar, pin)
      navigate('/play/levels')
    } catch (e) {
      setError(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  // ---- Show player code after register ----
  if (registered) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 text-center relative overflow-hidden" style={BG}>
        <div className="absolute inset-0 pointer-events-none motion-reduce:hidden" aria-hidden="true">
          {EMBERS.map((e, i) => (
            <span key={i}
              className="absolute bottom-[35%] rounded-full bg-ember-glow animate-drift-ember"
              style={{ left: e.left, width: e.size, height: e.size, animationDelay: e.delay, animationDuration: e.duration,
                       boxShadow: '0 0 6px 2px rgba(255,208,138,0.5)' }} />
          ))}
        </div>

        <div className="relative mb-5 motion-safe:animate-float w-28 h-28">
          <div className="absolute inset-0 rounded-full bg-brand-green/20 blur-2xl motion-safe:animate-pulse-slow" />
          <Creature species={avatar} className="relative w-full h-full drop-shadow-xl" />
        </div>
        <h1 className="font-vm-display text-4xl font-bold text-white mb-2 flex items-center justify-center gap-2">
          You're in, {AVATAR_NAMES[avatar]}! <PartyPopper className="w-8 h-8 text-brand-amber" />
        </h1>
        <p className="text-white/50 mb-8 relative z-10 flex items-center justify-center gap-1.5">
          Write this down so you can log back in: <SpeakButton onClick={replayRegistered} />
        </p>
        <GlassPanel className="mb-6 w-full max-w-xs" accent="brand-green">
          <p className="text-white/40 text-sm mb-1">Your Player Code</p>
          <p className="font-vm-display text-4xl font-bold text-brand-green tracking-widest mb-4">
            {registered.player_code}
          </p>
          <p className="text-white/40 text-sm mb-1">Your PIN</p>
          <p className="font-vm-display text-3xl font-bold text-brand-amber tracking-widest">
            {'•'.repeat(pin.length)}
          </p>
        </GlassPanel>
        <p className="text-white/30 text-xs mb-8 relative z-10">Show this to your teacher too!</p>
        <Button size="lg" onClick={() => navigate('/play/levels')} className="relative z-10 gap-2">
          Let's Play! <ArrowRight className="w-4 h-4" />
        </Button>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 relative overflow-hidden" style={BG}>
      <div className="absolute inset-0 pointer-events-none motion-reduce:hidden" aria-hidden="true">
        {EMBERS.map((e, i) => (
          <span key={i}
            className="absolute bottom-[30%] rounded-full bg-ember-glow animate-drift-ember"
            style={{ left: e.left, width: e.size, height: e.size, animationDelay: e.delay, animationDuration: e.duration,
                     boxShadow: '0 0 6px 2px rgba(255,208,138,0.5)' }} />
        ))}
      </div>

      {mode === 'choose' && (
        <Link to="/" className="absolute top-6 left-6 text-white/30 hover:text-white/60 text-sm z-10 flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" /> Back
        </Link>
      )}

      {/* Mode chooser — action buttons come right after a short intro,
          not after the full game-preview row. The badges used to sit
          between the intro and these buttons, pushing New Player/I have
          a code below the fold on first visit; they're now a compact
          teaser underneath instead of a scroll gate in front of them. */}
      {mode === 'choose' && (
        <div className="text-center w-full max-w-sm relative z-10">
          <WelcomeCrew />
          <h1 className="font-vm-display text-2xl font-bold text-white mb-2 leading-tight">
            Blow, speak, and watch the world move.
          </h1>

          {/* A felt moment, not just a claim -- breath literally moving a
              game object, before any signup. Nothing else in this space
              does breath-driven gameplay, so this is worth showing, not
              just saying in marketing copy. */}
          <div className="flex items-center justify-center gap-2 mb-3">
            <span className="text-2xl motion-safe:animate-pulse-slow" style={{ animationDuration: '2.2s' }}>🌬️</span>
            <span className="text-white/30 text-xs">→</span>
            <span className="text-2xl motion-safe:animate-float" style={{ animationDuration: '2.2s' }}>🎈</span>
          </div>

          <p className="text-white/40 mb-2 flex items-center justify-center gap-1.5 text-sm">
            Ready to play? <SpeakButton onClick={replayChoose} />
          </p>

          {/* No-therapist trust badge -- most competitors assume a clinic
              relationship or don't support one at all; worth stating
              plainly since it's a real acquisition lever, not buried
              backend logic. */}
          <p className="text-white/25 text-xs mb-6">
            Works with or without a therapist.
          </p>
          <div className="flex flex-col gap-4">
            <button onClick={() => setMode('register')}
              className={`group relative overflow-hidden rounded-[2rem] p-6 text-left
                         bg-gradient-to-br from-brand-amber/20 to-dusk-mid/50 backdrop-blur-sm border-2 border-brand-amber/40
                         hover:border-brand-amber hover:-translate-y-1 hover:shadow-xl hover:shadow-brand-amber/20
                         focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-amber focus-visible:ring-offset-2 focus-visible:ring-offset-[#12142E]
                         transition-all duration-300 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
              style={{ transitionDelay: mounted ? '0ms' : '0ms' }}>
              <div className="absolute -top-6 -right-6 w-24 h-24 rounded-full bg-brand-amber/10 blur-2xl
                              group-hover:bg-brand-amber/20 transition-colors duration-300" />
              <div className="relative flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-brand-amber/15 border border-brand-amber/25 flex items-center
                                justify-center flex-shrink-0 group-hover:scale-110 transition-transform duration-300">
                  <Sparkles className="w-6 h-6 text-brand-amber" />
                </div>
                <div>
                  <p className="font-vm-display text-xl font-bold text-white">New Player</p>
                  <p className="text-white/40 text-sm">Create your account</p>
                </div>
              </div>
            </button>
            <button onClick={() => setMode('login')}
              className={`group relative overflow-hidden rounded-[2rem] p-6 text-left
                         bg-gradient-to-br from-brand-green/20 to-dusk-mid/50 backdrop-blur-sm border-2 border-brand-green/40
                         hover:border-brand-green hover:-translate-y-1 hover:shadow-xl hover:shadow-brand-green/20
                         focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-green focus-visible:ring-offset-2 focus-visible:ring-offset-[#12142E]
                         transition-all duration-300 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
              style={{ transitionDelay: mounted ? '90ms' : '0ms' }}>
              <div className="absolute -top-6 -right-6 w-24 h-24 rounded-full bg-brand-green/10 blur-2xl
                              group-hover:bg-brand-green/20 transition-colors duration-300" />
              <div className="relative flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-brand-green/15 border border-brand-green/25 flex items-center
                                justify-center flex-shrink-0 group-hover:scale-110 transition-transform duration-300">
                  <KeyRound className="w-6 h-6 text-brand-green" />
                </div>
                <div>
                  <p className="font-vm-display text-xl font-bold text-white">I have a code</p>
                  <p className="text-white/40 text-sm">Log back in</p>
                </div>
              </div>
            </button>
            <button onClick={() => setMode('assessment')}
              className={`group relative overflow-hidden rounded-[2rem] p-6 text-left
                         bg-gradient-to-br from-brand-coral/20 to-dusk-mid/50 backdrop-blur-sm border-2 border-brand-coral/40
                         hover:border-brand-coral hover:-translate-y-1 hover:shadow-xl hover:shadow-brand-coral/20
                         focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-coral focus-visible:ring-offset-2 focus-visible:ring-offset-[#12142E]
                         transition-all duration-300 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
              style={{ transitionDelay: mounted ? '180ms' : '0ms' }}>
              <div className="absolute -top-6 -right-6 w-24 h-24 rounded-full bg-brand-coral/10 blur-2xl
                              group-hover:bg-brand-coral/20 transition-colors duration-300" />
              <div className="relative flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-brand-coral/15 border border-brand-coral/25 flex items-center
                                justify-center flex-shrink-0 group-hover:scale-110 transition-transform duration-300">
                  <Stethoscope className="w-6 h-6 text-brand-coral" />
                </div>
                <div>
                  <p className="font-vm-display text-xl font-bold text-white">My Therapist Set Me Up</p>
                  <p className="text-white/40 text-sm">Find your name</p>
                </div>
              </div>
            </button>
          </div>

          {/* Language badge -- the assessment flow genuinely supports 8
              Indian languages (see routes/assessment.py's valid_languages),
              which almost nothing else in this market does. Worth
              surfacing at first contact, not buried in a settings screen. */}
          <p className="text-white/25 text-xs mt-10 mb-1">
            Practice in English, Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, or Marathi.
          </p>

          {/* Game preview — a teaser below the actual actions now, not a
              row you have to get past first. One line, horizontally
              scrollable so all 5 fit without wrapping on narrow screens. */}
          <p className="text-white/30 text-xs mt-3 mb-3">Five ways to practice, all in one place.</p>
          {/* Named badges, wrapping onto 2 short lines rather than forced
              onto one -- 5 full names don't fit one line at this width
              without becoming unreadable. Popover opens ABOVE the row
              (bottom-full, not top-full): this row sits near the bottom
              of the page, and the page wrapper's overflow-hidden was
              clipping a below-row popover out of view entirely. */}
          <div className="relative flex flex-wrap items-center justify-center gap-2">
            {GAMES.map((g) => (
              <button
                key={g.key}
                type="button"
                onClick={() => setActiveGame(cur => cur === g.key ? null : g.key)}
                aria-expanded={activeGame === g.key}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-all
                            hover:-translate-y-0.5 active:scale-95 whitespace-nowrap ${g.badgeClass}
                            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70
                            ${activeGame === g.key ? 'ring-2 ring-white/40' : ''}`}
              >
                {g.emoji} {g.name}
              </button>
            ))}

            {activeGame && (() => {
              const g = GAMES.find(x => x.key === activeGame)
              return (
                <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 w-64 z-20
                                bg-dusk-mid/95 backdrop-blur-md border border-white/15 rounded-2xl
                                p-4 text-left shadow-xl">
                  <button onClick={() => setActiveGame(null)}
                          className="absolute top-2 right-2 text-white/30 hover:text-white/60 text-xs">
                    ✕
                  </button>
                  <p className="font-vm-display text-white font-bold mb-1">{g.emoji} {g.name}</p>
                  <p className="text-white/50 text-sm">{g.desc}</p>
                </div>
              )
            })()}
          </div>
        </div>
      )}

      {/* Register */}
      {mode === 'register' && registerStep === 'form' && (
        <GlassPanel accent="brand-amber" className="w-full max-w-sm relative z-10">
          <button onClick={() => { setMode('choose'); setPin(''); setError(''); setRegisterStep('form'); setParentEmail(''); setParentPhone('') }}
                  className="text-white/30 hover:text-white/60 text-sm mb-6 transition-colors flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" /> Back
          </button>
          <h1 className="font-vm-display text-3xl font-bold text-white mb-6 text-center flex items-center justify-center gap-2">
            Create Account <SpeakButton onClick={replayRegister} className="text-white/25 hover:text-white/50" />
          </h1>

          {/* Name */}
          <div className="mb-5">
            <label className="text-sm text-white/50 block mb-1">Your first name</label>
            <input className="input text-lg" placeholder="e.g. Alex"
                   value={firstName} onChange={e => setFirstName(e.target.value)} />
          </div>

          {/* Avatar — real illustrated creatures now, not bare emoji */}
          <label className="text-sm text-white/50 block mb-3">Pick your character</label>
          <div className="grid grid-cols-3 gap-3 mb-6">
            {AVATARS.map(av => (
              <button key={av} onClick={() => setAvatar(av)} aria-pressed={avatar === av}
                className="flex flex-col items-center gap-1.5 group rounded-2xl
                           focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70">
                <div className={`rounded-full p-1 transition-all
                  ${avatar === av ? 'ring-2 ring-brand-green scale-110 shadow-lg shadow-brand-green/30' : 'ring-2 ring-transparent group-hover:ring-white/20'}`}>
                  <Avatar avatar={av} size="lg" />
                </div>
                <span className={`text-xs font-semibold transition-colors
                  ${avatar === av ? 'text-brand-green' : 'text-white/35 group-hover:text-white/60'}`}>
                  {AVATAR_NAMES[av]}
                </span>
              </button>
            ))}
          </div>

          {/* PIN */}
          <label className="text-sm text-white/50 block mb-2">Choose a 4-digit PIN</label>
          <PinDots length={pin.length} />
          <PinPad onDigit={handlePin} onDelete={deletePin} />

          {error && <p className="text-brand-coral text-sm text-center mb-3">{error}</p>}
          <Button className="w-full gap-2" size="lg" onClick={handleContinueToParentContact} disabled={loading}>
            Continue <ArrowRight className="w-4 h-4" />
          </Button>
        </GlassPanel>
      )}

      {/* Register — parent contact info (COPPA: a parent's email + phone
          are required before we create the account). Sends the email OTP
          once both fields are filled; the phone OTP is requested right
          after the email code is confirmed (see the verifyEmail/verifyPhone
          steps below). */}
      {mode === 'register' && registerStep === 'parentContact' && (
        <GlassPanel accent="brand-amber" className="w-full max-w-sm relative z-10">
          <button onClick={() => { setRegisterStep('form'); setError('') }}
                  className="text-white/30 hover:text-white/60 text-sm mb-6 transition-colors flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" /> Back
          </button>
          <div className="flex justify-center gap-2 mb-4">
            <div className="w-12 h-12 rounded-2xl bg-brand-amber/15 border border-brand-amber/25 flex items-center justify-center">
              <Mail className="w-6 h-6 text-brand-amber" />
            </div>
            <div className="w-12 h-12 rounded-2xl bg-brand-amber/15 border border-brand-amber/25 flex items-center justify-center">
              <Phone className="w-6 h-6 text-brand-amber" />
            </div>
          </div>
          <h1 className="font-vm-display text-2xl font-bold text-white mb-2 text-center">
            Almost there, {firstName.trim() || 'friend'}!
          </h1>
          <p className="text-white/50 text-sm text-center mb-6">
            We need a parent's email and phone number to finish creating your account.
          </p>
          <div className="mb-4">
            <label className="text-sm text-white/50 block mb-1">Parent's email</label>
            <input type="email" className="input text-lg" placeholder="parent@example.com"
                   value={parentEmail} onChange={e => setParentEmail(e.target.value)} />
          </div>
          <div className="mb-5">
            <label className="text-sm text-white/50 block mb-1">Parent's phone number</label>
            <input type="tel" className="input text-lg" placeholder="+1 555 123 4567"
                   value={parentPhone} onChange={e => setParentPhone(e.target.value)} />
          </div>
          {error && <p className="text-brand-coral text-sm text-center mb-3">{error}</p>}
          <Button className="w-full gap-2" size="lg" onClick={handleSendParentContact} disabled={loading}>
            {loading ? 'Sending…' : <>Continue <ArrowRight className="w-4 h-4" /></>}
          </Button>
        </GlassPanel>
      )}

      {/* Register — verify parent email (code sent by handleSendParentContact) */}
      {mode === 'register' && registerStep === 'verifyEmail' && (
        <GlassPanel accent="brand-amber" className="w-full max-w-sm relative z-10">
          <button onClick={() => { setRegisterStep('parentContact'); setError(''); setEmailCode(''); setResendMsg('') }}
                  className="text-white/30 hover:text-white/60 text-sm mb-6 transition-colors flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" /> Back
          </button>
          <div className="flex justify-center mb-4">
            <div className="w-12 h-12 rounded-2xl bg-brand-amber/15 border border-brand-amber/25 flex items-center justify-center">
              <Mail className="w-6 h-6 text-brand-amber" />
            </div>
          </div>
          <h1 className="font-vm-display text-2xl font-bold text-white mb-2 text-center">
            Check that email!
          </h1>
          <p className="text-white/50 text-sm text-center mb-6">
            We sent a 6-digit code to {parentEmail.trim()}. Ask a parent to enter it below.
          </p>
          <div className="mb-5">
            <label className="text-sm text-white/50 block mb-1">Verification code</label>
            <input type="text" inputMode="numeric" maxLength={6} className="input text-lg tracking-widest text-center"
                   placeholder="123456" value={emailCode}
                   onChange={e => setEmailCode(e.target.value.replace(/\D/g, ''))} />
          </div>
          {error && <p className="text-brand-coral text-sm text-center mb-3">{error}</p>}
          {resendMsg && !error && <p className="text-mint-light text-sm text-center mb-3">{resendMsg}</p>}
          <Button className="w-full gap-2 mb-3" size="lg" onClick={handleConfirmEmailCode} disabled={loading}>
            {loading ? 'Checking…' : <>Verify Code <ArrowRight className="w-4 h-4" /></>}
          </Button>
          <button onClick={handleResendEmailCode} disabled={loading}
                  className="w-full text-center text-sm text-white/40 hover:text-white/70 transition-colors">
            Resend code
          </button>
        </GlassPanel>
      )}

      {/* Register — verify parent phone (code requested right after email confirms) */}
      {mode === 'register' && registerStep === 'verifyPhone' && (
        <GlassPanel accent="brand-amber" className="w-full max-w-sm relative z-10">
          <div className="flex justify-center mb-4">
            <div className="w-12 h-12 rounded-2xl bg-brand-amber/15 border border-brand-amber/25 flex items-center justify-center">
              <Phone className="w-6 h-6 text-brand-amber" />
            </div>
          </div>
          <h1 className="font-vm-display text-2xl font-bold text-white mb-2 text-center">
            One more code!
          </h1>
          <p className="text-white/50 text-sm text-center mb-6">
            We texted a 6-digit code to {parentPhone.trim()}. Ask a parent to enter it below.
          </p>
          <div className="mb-5">
            <label className="text-sm text-white/50 block mb-1">Verification code</label>
            <input type="text" inputMode="numeric" maxLength={6} className="input text-lg tracking-widest text-center"
                   placeholder="123456" value={phoneCode}
                   onChange={e => setPhoneCode(e.target.value.replace(/\D/g, ''))} />
          </div>
          {error && <p className="text-brand-coral text-sm text-center mb-3">{error}</p>}
          {resendMsg && !error && <p className="text-mint-light text-sm text-center mb-3">{resendMsg}</p>}
          <Button className="w-full gap-2 mb-3" size="lg" onClick={handleConfirmPhoneCode} disabled={loading}>
            {loading ? 'Creating…' : <>Create Account! <PartyPopper className="w-4 h-4" /></>}
          </Button>
          <button onClick={handleResendPhoneCode} disabled={loading}
                  className="w-full text-center text-sm text-white/40 hover:text-white/70 transition-colors">
            Resend code
          </button>
        </GlassPanel>
      )}

      {/* Login */}
      {mode === 'login' && (
        <GlassPanel accent="brand-green" className="w-full max-w-sm relative z-10">
          <button onClick={() => { setMode('choose'); setPin(''); setError('') }}
                  className="text-white/30 hover:text-white/60 text-sm mb-6 transition-colors flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" /> Back
          </button>
          <h1 className="font-vm-display text-3xl font-bold text-white mb-6 text-center flex items-center justify-center gap-2">
            Welcome Back! <SpeakButton onClick={replayLogin} className="text-white/25 hover:text-white/50" />
          </h1>

          <div className="mb-2">
            <label className="text-sm text-white/50 block mb-1">Your Name or Player Code</label>
            <input className="input text-center text-xl font-bold tracking-widest uppercase"
                   placeholder="e.g. CHICK42 or your name"
                   value={playerCode} onChange={e => setPlayerCode(e.target.value.toUpperCase())} />
          </div>
          <p className="text-white/30 text-xs text-center mb-4">
            Lost your player code? Just type your name instead!
          </p>

          <label className="text-sm text-white/50 block mb-2">Your PIN</label>
          <PinDots length={pin.length} />
          <PinPad onDigit={handlePin} onDelete={deletePin} />

          {error && <p className="text-brand-coral text-sm text-center mb-3">{error}</p>}
          <Button className="w-full gap-2" size="lg" onClick={handleLogin} disabled={loading}>
            {loading ? 'Checking…' : <>Let's Play! <ArrowRight className="w-4 h-4" /></>}
          </Button>
        </GlassPanel>
      )}

      {/* Assessment-linked setup */}
      {mode === 'assessment' && (
        <GlassPanel accent="brand-green" className="w-full max-w-sm relative z-10">
          <button onClick={() => { setMode('choose'); setPin(''); setError(''); setSelectedPatientId('') }}
                  className="text-white/30 hover:text-white/60 text-sm mb-6 transition-colors flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" /> Back
          </button>
          <h1 className="font-vm-display text-3xl font-bold text-white mb-6 text-center flex items-center justify-center gap-2">
            Find Your Name <SpeakButton onClick={replayAssessment} className="text-white/25 hover:text-white/50" />
          </h1>

          {candidatesLoading && <p className="text-white/40 text-center text-sm mb-4">Loading…</p>}
          {!candidatesLoading && candidatesError && (
            <div className="text-center mb-4">
              <p className="text-brand-coral text-sm mb-2">{candidatesError}</p>
              <button onClick={fetchCandidates}
                      className="text-white/50 hover:text-white text-xs underline underline-offset-2 transition-colors
                                 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70 rounded">
                Try again
              </button>
            </div>
          )}
          {!candidatesLoading && !candidatesError && candidates.length === 0 && (
            <p className="text-white/40 text-center text-sm mb-4">No names found yet. Ask your therapist!</p>
          )}

          {!candidatesLoading && candidates.length > 0 && !selectedPatientId && (
            <div className="flex flex-col gap-2 mb-2">
              {candidates.map(c => (
                <button key={c.id} onClick={() => setSelectedPatientId(c.id)}
                  className="w-full text-left rounded-2xl p-4 bg-white/5 hover:bg-white/10 border border-white/10
                             hover:border-brand-green/40 transition-all">
                  <p className="font-vm-display text-lg font-bold text-white">{c.name}</p>
                </button>
              ))}
            </div>
          )}

          {selectedPatientId && (
            <>
              <label className="text-sm text-white/50 block mb-3">Pick your character</label>
              <div className="grid grid-cols-3 gap-3 mb-6">
                {AVATARS.map(av => (
                  <button key={av} onClick={() => setAvatar(av)} aria-pressed={avatar === av}
                          className="flex flex-col items-center gap-1.5 group rounded-2xl
                                     focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70">
                    <div className={`rounded-full p-1 transition-all
                      ${avatar === av ? 'ring-2 ring-brand-green scale-110 shadow-lg shadow-brand-green/30' : 'ring-2 ring-transparent group-hover:ring-white/20'}`}>
                      <Avatar avatar={av} size="lg" />
                    </div>
                    <span className={`text-xs font-semibold transition-colors
                      ${avatar === av ? 'text-brand-green' : 'text-white/35 group-hover:text-white/60'}`}>
                      {AVATAR_NAMES[av]}
                    </span>
                  </button>
                ))}
              </div>

              <label className="text-sm text-white/50 block mb-2">Choose a 4-digit PIN</label>
              <PinDots length={pin.length} />
              <PinPad onDigit={handlePin} onDelete={deletePin} />

              {error && <p className="text-brand-coral text-sm text-center mb-3">{error}</p>}
              <Button className="w-full gap-2" size="lg" onClick={handleAssessmentSetup} disabled={loading}>
                {loading ? 'Setting up…' : <>Let's Play! <ArrowRight className="w-4 h-4" /></>}
              </Button>
            </>
          )}
        </GlassPanel>
      )}
    </div>
  )
}
