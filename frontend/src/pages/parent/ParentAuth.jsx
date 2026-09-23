import { useState, useEffect } from 'react'
import { useNavigate, Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { authAPI, getErrorMessage, getCrossRoleRedirect, stripCrossRoleTag, verifyAPI } from '../../api/client'
import GoogleAuthButton from '../../components/ui/GoogleAuthButton'
import { SavedProfilesGate, Avatar } from '../../components/ui'
import {
  Heart, LineChart, MessageCircle,
  Mail, Lock, User, KeyRound, Phone, Eye, EyeOff, ArrowLeft, Sparkles,
} from 'lucide-react'

const NEW_CHILD_AVATARS = ['chick', 'dragon', 'bunny', 'fox', 'rocket', 'fish']

const VALUE_PROPS = [
  { icon: LineChart, text: "See your child's progress across every game, in plain language" },
  { icon: MessageCircle, text: 'Message their therapist directly — no separate app to check' },
  { icon: Heart, text: 'Get simple home practice ideas picked for what they need most' },
]

function Field({ icon: Icon, rightElement, ...props }) {
  return (
    <div className="relative">
      <Icon className="w-4 h-4 text-paper/30 absolute left-4 top-1/2 -translate-y-1/2" />
      <input
        {...props}
        className="w-full bg-ink border border-white/10 rounded-xl pl-11 pr-11 py-3 text-paper
                   placeholder:text-paper/30 focus:outline-none focus:border-coral/50 transition-colors"
      />
      {rightElement && (
        <div className="absolute right-4 top-1/2 -translate-y-1/2">{rightElement}</div>
      )}
    </div>
  )
}

// Wrapped by the default export below with SavedProfilesGate, so anyone
// who has a saved parent profile on this device sees a "who's continuing"
// picker instead of this form -- see SavedProfilesGate.jsx.
function ParentAuthForm() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [sessionExpired] = useState(() => searchParams.get('session_expired') === '1')
  // Set when a kid tapped "Ask a grown-up to start a free trial" on their
  // post-assessment report -- see AssessmentReport.jsx. Without this
  // context, landing here looked exactly like getting logged out with no
  // explanation: one session is active at a time, so a parent signing in
  // here does replace the kid's active session, but their PIN/profile is
  // already saved (see AuthContext.jsx's _persistSession/knownAccounts) --
  // this banner is just making that switch, and the easy way back, visible
  // instead of silent.
  const [fromKidTrial] = useState(() => searchParams.get('from') === 'kid_trial')
  const kidTrialName = searchParams.get('kid') || ''
  const { loginParent, registerParent, loginParentGoogle, registerParentGoogle } = useAuth()
  const [mode, setMode] = useState('login')
  // Prefilled when redirected here from the therapist login page after a
  // cross-role email conflict (see client.js's getCrossRoleRedirect) --
  // no reason to make them retype an email we already have.
  const [form, setForm] = useState({
    code: '', email: searchParams.get('email') || '', password: '', fullName: '', phone: '',
  })
  // 'code': the existing flow, entering a player/invite code from a
  // therapist or a self-registered kid. 'newChild': no code yet --
  // create the parent AND child account together (POST
  // /auth/parent-kid-register, already wired up in AuthContext's
  // registerParent via codeType: 'new_child'). This is the only path
  // left for a therapist-free family to get their FIRST account, now
  // that kids can't self-register (see Play.jsx's "New here?" panel).
  const [registerFlow, setRegisterFlow] = useState('code')
  const [newChildForm, setNewChildForm] = useState({ firstName: '', avatar: 'chick', pin: '' })
  const [newChildStep, setNewChildStep] = useState('form') // form | verifyEmail
  const [newChildEmailCode, setNewChildEmailCode] = useState('')
  const [newChildResendMsg, setNewChildResendMsg] = useState('')
  const [newChildCooldown, setNewChildCooldown] = useState(0)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [showRecovery, setShowRecovery] = useState(false)
  const [recoveryEmail, setRecoveryEmail] = useState('')
  const [recoveryStatus, setRecoveryStatus] = useState('') // '' | 'sending' | 'sent'

  // Forgot-password: same OTP round-trip as forgot-PIN in Play.jsx
  // (verifyAPI.request/.confirm), then reset in the same call that
  // confirms the code. Separate panel from the player-code recovery
  // above -- different problem, different backend endpoint.
  const [showForgotPassword, setShowForgotPassword] = useState(false)
  const [resumedAfterVerify, setResumedAfterVerify] = useState(false)
  const [forgotStep, setForgotStep] = useState('request') // request | verify | done
  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotCode, setForgotCode] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [forgotError, setForgotError] = useState('')
  const [forgotBusy, setForgotBusy] = useState(false)
  const [forgotResendMsg, setForgotResendMsg] = useState('')
  const [forgotCooldown, setForgotCooldown] = useState(0)

  // Resend cooldown -- same pattern as Verify.jsx, prevents spamming the
  // email-send endpoint via this "Resend code" button.
  useEffect(() => {
    if (forgotCooldown <= 0) return
    const t = setInterval(() => setForgotCooldown((c) => Math.max(0, c - 1)), 1000)
    return () => clearInterval(t)
  }, [forgotCooldown])

  useEffect(() => {
    if (newChildCooldown <= 0) return
    const t = setInterval(() => setNewChildCooldown((c) => Math.max(0, c - 1)), 1000)
    return () => clearInterval(t)
  }, [newChildCooldown])

  // "New child, no therapist" registration was removed (parents now only
  // link to a child via the player code a therapist gives them); drop any
  // stale entry left over from that flow so it doesn't linger forever.
  useEffect(() => {
    localStorage.removeItem('bq_pending_parent_kid_register')
  }, [])

  // Same pattern as therapist/Login.jsx's ALREADY_EXISTS -- match the
  // message it uses for a same-role duplicate specifically, so this
  // doesn't also fire on the (differently-worded) cross-role message,
  // which is handled separately via getCrossRoleRedirect below.
  const ALREADY_EXISTS = /account already exists/i

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (mode === 'login') {
        await loginParent(form.email, form.password)
      } else {
        await registerParent({
          code: form.code, codeType: 'player_code', email: form.email, password: form.password,
          fullName: form.fullName, phone: form.phone,
        })
      }
      localStorage.removeItem('bq_pending_parent_kid_register')
      navigate('/parent/dashboard')
    } catch (err) {
      if (getCrossRoleRedirect(err) === 'therapist') {
        navigate(`/therapist/login?email=${encodeURIComponent(form.email.trim())}`)
        return
      }
      const msg = getErrorMessage(err, 'Something went wrong — please try again.')
      if (mode === 'register' && ALREADY_EXISTS.test(msg)) {
        setMode('login')
      }
      setError(stripCrossRoleTag(msg))
    } finally {
      setBusy(false)
    }
  }

  // Google sign-in has no email/password step, so there's nothing to
  // "submit" a form around -- called directly from GoogleAuthButton's
  // onIdToken. Login just needs the token; register additionally needs
  // a player/invite code (see registerParentGoogle's docstring on why
  // "new child, no therapist" isn't supported here), so the button is
  // gated on that field being filled in register mode -- see disabled
  // prop below.
  async function handleGoogle(idToken) {
    setError('')
    setBusy(true)
    try {
      if (mode === 'login') {
        await loginParentGoogle(idToken)
      } else {
        await registerParentGoogle({ idToken, code: form.code, phone: form.phone })
      }
      navigate('/parent/dashboard')
    } catch (err) {
      if (getCrossRoleRedirect(err) === 'therapist') {
        navigate('/therapist/login')
        return
      }
      setError(getErrorMessage(err, 'Something went wrong — please try again.'))
    } finally {
      setBusy(false)
    }
  }

  async function handleForgotPlayerCode(e) {
    e.preventDefault()
    setRecoveryStatus('sending')
    try {
      await authAPI.forgotPlayerCode({ email: recoveryEmail })
    } catch {
      // Intentionally ignored -- the backend already returns the same
      // generic response whether or not the email matched an account,
      // so surfacing a network-level error here would still leak more
      // than the endpoint itself is designed to reveal. Worst case,
      // the user sees the generic message and tries again.
    } finally {
      setRecoveryStatus('sent')
    }
  }

  function resetForgotPasswordFlow() {
    setForgotStep('request'); setForgotEmail(''); setForgotCode('')
    setNewPassword(''); setForgotError(''); setForgotResendMsg(''); setForgotCooldown(0)
  }

  async function handleForgotPasswordSendCode(e) {
    e.preventDefault()
    if (!forgotEmail.trim()) { setForgotError('Enter your email'); return }
    setForgotError(''); setForgotResendMsg(''); setForgotBusy(true)
    try {
      await verifyAPI.request({ email: forgotEmail.trim() })
      setForgotStep('verify')
      setForgotCooldown(60)
    } catch (err) {
      setForgotError(getErrorMessage(err, "Couldn't send the code — try again"))
    } finally {
      setForgotBusy(false)
    }
  }

  async function handleForgotPasswordResend() {
    setForgotError(''); setForgotResendMsg(''); setForgotBusy(true)
    try {
      await verifyAPI.request({ email: forgotEmail.trim() })
      setForgotResendMsg('Code resent!')
      setForgotCooldown(60)
    } catch (err) {
      setForgotError(getErrorMessage(err, "Couldn't resend the code — try again"))
    } finally {
      setForgotBusy(false)
    }
  }

  async function handleForgotPasswordConfirm(e) {
    e.preventDefault()
    if (forgotCode.trim().length !== 6) { setForgotError('Enter the 6-digit code'); return }
    if (newPassword.length < 8)         { setForgotError('Password must be at least 8 characters'); return }
    setForgotError(''); setForgotBusy(true)
    try {
      await verifyAPI.confirm({ email: forgotEmail.trim(), code: forgotCode.trim() })
    } catch (err) {
      setForgotError(getErrorMessage(err, "That code didn't work — try again"))
      setForgotBusy(false)
      return
    }
    try {
      await authAPI.parentResetPassword({ email: forgotEmail.trim(), new_password: newPassword })
      setForgotStep('done')
    } catch (err) {
      setForgotError(getErrorMessage(err, "Couldn't reset the password — try again"))
    } finally {
      setForgotBusy(false)
    }
  }

  function updateNewChild(field) {
    return (e) => setNewChildForm((f) => ({ ...f, [field]: e.target.value }))
  }

  // Step 1: validate the whole form (parent's own email/password + the
  // child's name/PIN), then send the parent an OTP -- same COPPA gate
  // POST /auth/parent-kid-register enforces server-side (check_email_
  // consent), just surfaced here instead of a generic 403 after the fact.
  async function handleSendNewChildVerification(e) {
    e.preventDefault()
    if (!newChildForm.firstName.trim()) { setError("Enter your child's name"); return }
    if (!/^\d{4}$/.test(newChildForm.pin)) { setError('PIN must be exactly 4 digits'); return }
    if (!form.email.trim()) { setError('Enter your email'); return }
    if (!form.password || form.password.length < 8) { setError('Password must be at least 8 characters'); return }
    if (!form.phone.trim()) { setError('Enter your phone number'); return }
    setError(''); setBusy(true)
    try {
      await verifyAPI.request({ email: form.email.trim(), purpose: 'register_parent' })
      setNewChildStep('verifyEmail')
      setNewChildCooldown(60)
    } catch (err) {
      if (getCrossRoleRedirect(err) === 'therapist') {
        navigate(`/therapist/login?email=${encodeURIComponent(form.email.trim())}`)
        return
      }
      setError(getErrorMessage(err, "Couldn't send the verification code — try again"))
    } finally {
      setBusy(false)
    }
  }

  async function handleResendNewChildCode() {
    setError(''); setNewChildResendMsg(''); setBusy(true)
    try {
      await verifyAPI.request({ email: form.email.trim(), purpose: 'register_parent' })
      setNewChildResendMsg('Code resent!')
      setNewChildCooldown(60)
    } catch (err) {
      if (getCrossRoleRedirect(err) === 'therapist') {
        navigate(`/therapist/login?email=${encodeURIComponent(form.email.trim())}`)
        return
      }
      setError(getErrorMessage(err, "Couldn't resend the code — try again"))
    } finally {
      setBusy(false)
    }
  }

  // Step 2: confirm the code, then create both accounts in one call.
  async function handleConfirmNewChildCode(e) {
    e.preventDefault()
    if (newChildEmailCode.trim().length !== 6) { setError('Enter the 6-digit code'); return }
    setError(''); setBusy(true)
    try {
      await verifyAPI.confirm({ email: form.email.trim(), code: newChildEmailCode.trim() })
    } catch (err) {
      setError(getErrorMessage(err, "That code didn't work — try again"))
      setBusy(false)
      return
    }
    try {
      await registerParent({
        codeType: 'new_child',
        email: form.email, password: form.password, fullName: form.fullName, phone: form.phone,
        kidFirstName: newChildForm.firstName, kidAvatar: newChildForm.avatar, kidPin: newChildForm.pin,
      })
      navigate('/parent/dashboard')
    } catch (err) {
      if (getCrossRoleRedirect(err) === 'therapist') {
        navigate(`/therapist/login?email=${encodeURIComponent(form.email.trim())}`)
        return
      }
      setError(getErrorMessage(err, "Couldn't create your account — try again"))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2" style={{ background: '#081A1C' }}>

      {/* Value-prop panel — same split-screen pattern as the therapist login,
          themed in the ink/coral palette this page (and ParentDashboard)
          actually live in, not the brand.* BreathQuest palette. */}
      <div className="hidden lg:flex flex-col justify-center px-16 relative overflow-hidden"
           style={{ background: 'radial-gradient(ellipse at 30% 20%, #D14A36 0%, #16221F 55%, #081A1C 100%)' }}>
        <div className="absolute -top-24 -left-24 w-72 h-72 rounded-full bg-coral/10 blur-3xl" />
        <div className="absolute bottom-0 right-0 w-96 h-96 rounded-full bg-coral-dark/10 blur-3xl" />

        <div className="relative z-10 max-w-sm">
          <div className="w-14 h-14 rounded-2xl bg-coral/15 border border-coral/25 flex items-center justify-center mb-8">
            <Heart className="w-7 h-7 text-coral-light" />
          </div>
          <h1 className="font-vm-display text-4xl font-bold text-paper leading-tight mb-4">
            Watch their progress unfold, one session at a time.
          </h1>
          <p className="text-paper/50 mb-10">
            Link your account to your child's game code and stay close to the work they're doing.
          </p>

          <div className="flex flex-col gap-5">
            {VALUE_PROPS.map(({ icon: Icon, text }, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-coral/10 border border-coral/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Icon className="w-4 h-4 text-coral-light" />
                </div>
                <p className="text-paper/70 text-sm leading-relaxed pt-1">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-center p-6 py-16">
        <div className="w-full max-w-md">
          <Link to="/" className="inline-flex items-center gap-2 text-paper/50 hover:text-paper
                                  hover:bg-white/5 transition-colors mb-8 text-sm font-medium
                                  -ml-3 px-3 py-1.5 rounded-full">
            <ArrowLeft className="w-4 h-4" /> Back
          </Link>

          <div className="mb-8 lg:hidden text-center">
            <div className="w-14 h-14 rounded-2xl bg-coral/15 border border-coral/25 flex items-center justify-center mx-auto mb-4">
              <Heart className="w-7 h-7 text-coral-light" />
            </div>
            <h1 className="font-vm-display text-2xl font-bold text-paper">Parent Portal</h1>
          </div>

          <div className="mb-6 hidden lg:block">
            <h2 className="font-vm-display text-2xl font-bold text-paper">
              {mode === 'login' ? 'Welcome back' : 'Create your account'}
            </h2>
            <p className="text-paper/40 text-sm mt-1">
              {mode === 'login' ? "Keep track of your child's progress" : "Link your account to your child's profile"}
            </p>
          </div>

          <div className="bg-ink-light border border-white/10 rounded-3xl p-8">
            <div className="flex bg-ink rounded-xl p-1 mb-6 border border-white/10">
              {['login', 'register'].map(m => (
                <button key={m} type="button" onClick={() => { setMode(m); setError(''); setResumedAfterVerify(false) }}
                  className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all
                    ${mode === m ? 'bg-coral text-paper shadow-sm' : 'text-paper/50 hover:text-paper'}`}>
                  {m === 'login' ? 'Sign In' : 'Register'}
                </button>
              ))}
            </div>

            {resumedAfterVerify && (
              <div className="bg-mint/10 border border-mint/30 rounded-xl px-4 py-3 text-sm text-mint-light mb-5">
                Email verified! Your details are saved below — just re-enter your password to finish creating your account.
              </div>
            )}

            {!resumedAfterVerify && sessionExpired && mode === 'login' && (
              <div className="bg-coral/10 border border-coral/30 rounded-xl px-4 py-3 text-sm text-coral-light mb-5">
                You were signed out after a while — sign in again to continue.
              </div>
            )}

            {!resumedAfterVerify && fromKidTrial && (
              <div className="bg-mint/10 border border-mint/30 rounded-xl px-4 py-3 text-sm text-mint-light mb-5">
                {kidTrialName ? `${kidTrialName}'s session is` : "Your child's session is"} saved — sign in here to
                start a free trial, then switch straight back with no PIN needed (look for "Switch profile" in the sidebar).
              </div>
            )}

            {mode === 'login' && (
              <>
                <GoogleAuthButton onIdToken={handleGoogle} onError={setError} disabled={busy} />
                <div className="flex items-center gap-3 my-5">
                  <div className="flex-1 h-px bg-white/10" />
                  <span className="text-paper/30 text-xs font-medium">or</span>
                  <div className="flex-1 h-px bg-white/10" />
                </div>
              </>
            )}

            {/* First-time guidance, register mode only: most new parents
                land here not knowing whether they need a code first.
                Spelled out plainly rather than assumed, since a code-only
                form with no explanation of where to get one is exactly
                the kind of thing that leaves a first-time user stuck. */}
            {mode === 'register' && (
              <div className="flex bg-ink rounded-xl p-1 mb-5 border border-white/10">
                <button type="button" onClick={() => { setRegisterFlow('code'); setError('') }}
                  className={`flex-1 py-2 rounded-lg text-xs font-semibold transition-all
                    ${registerFlow === 'code' ? 'bg-white/10 text-paper' : 'text-paper/45 hover:text-paper/70'}`}>
                  I have a code
                </button>
                <button type="button" onClick={() => { setRegisterFlow('newChild'); setError('') }}
                  className={`flex-1 py-2 rounded-lg text-xs font-semibold transition-all
                    ${registerFlow === 'newChild' ? 'bg-white/10 text-paper' : 'text-paper/45 hover:text-paper/70'}`}>
                  Start fresh, no code yet
                </button>
              </div>
            )}

            {mode === 'register' && registerFlow === 'newChild' ? (
              newChildStep === 'form' ? (
                <form onSubmit={handleSendNewChildVerification} className="flex flex-col gap-4">
                  <p className="text-paper/40 text-xs leading-relaxed px-1">
                    Not working with a therapist yet? Create your account and your child's
                    together -- you'll pick their name, character and PIN, and we'll email
                    you a code to confirm it's really you.
                  </p>

                  <div>
                    <p className="text-paper/50 text-xs font-medium mb-2">Your child</p>
                    <Field icon={User} type="text" required placeholder="Child's first name"
                      value={newChildForm.firstName} onChange={updateNewChild('firstName')} />
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    {NEW_CHILD_AVATARS.map((a) => (
                      <button type="button" key={a}
                        onClick={() => setNewChildForm((f) => ({ ...f, avatar: a }))}
                        className={`rounded-full transition-all duration-200 hover:-translate-y-0.5
                                    ${newChildForm.avatar === a ? 'ring-2 ring-coral scale-110' : 'opacity-60 hover:opacity-100'}`}>
                        <Avatar avatar={a} size="sm" />
                      </button>
                    ))}
                  </div>
                  <Field icon={KeyRound} type="text" required inputMode="numeric" maxLength={4}
                    placeholder="Child's 4-digit PIN"
                    value={newChildForm.pin}
                    onChange={(e) => setNewChildForm((f) => ({ ...f, pin: e.target.value.replace(/\D/g, '').slice(0, 4) }))} />

                  <p className="text-paper/50 text-xs font-medium mt-2 mb-1">Your account</p>
                  <Field icon={Mail} type="email" required placeholder="Your email" autoComplete="email"
                    value={form.email} onChange={update('email')} />
                  <Field icon={Phone} type="tel" required autoComplete="tel"
                    placeholder="Your phone number"
                    value={form.phone} onChange={update('phone')} />
                  <Field icon={User} type="text" placeholder="Your name (optional)" autoComplete="name"
                    value={form.fullName} onChange={update('fullName')} />
                  <Field
                    icon={Lock}
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    placeholder="Password"
                    value={form.password}
                    onChange={update('password')}
                    rightElement={
                      <button type="button" onClick={() => setShowPassword(s => !s)}
                              className="text-paper/30 hover:text-paper/60 transition-colors">
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    }
                  />

                  {error && (
                    <div className="bg-coral/10 border border-coral/30 rounded-xl px-4 py-3 text-coral-light text-sm">
                      {error}
                    </div>
                  )}

                  <button type="submit" disabled={busy}
                    className="w-full bg-coral text-paper font-semibold rounded-xl py-3 mt-2
                               hover:bg-coral-dark transition-colors disabled:opacity-50 active:scale-95">
                    {busy ? 'Sending code…' : 'Send verification code'}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleConfirmNewChildCode} className="flex flex-col gap-4">
                  <p className="text-paper/40 text-xs leading-relaxed px-1">
                    We sent a 6-digit code to <span className="text-paper/60 font-medium">{form.email}</span>.
                    Enter it below to finish creating both accounts.
                  </p>
                  <Field icon={Sparkles} type="text" required inputMode="numeric" maxLength={6}
                    placeholder="6-digit code"
                    value={newChildEmailCode}
                    onChange={(e) => setNewChildEmailCode(e.target.value.replace(/\D/g, '').slice(0, 6))} />

                  {error && (
                    <div className="bg-coral/10 border border-coral/30 rounded-xl px-4 py-3 text-coral-light text-sm">
                      {error}
                    </div>
                  )}
                  {newChildResendMsg && (
                    <p className="text-mint-light text-xs">{newChildResendMsg}</p>
                  )}

                  <div className="flex gap-2">
                    <button type="button" onClick={() => { setNewChildStep('form'); setError(''); setNewChildEmailCode('') }}
                      className="flex-1 px-4 py-2.5 rounded-xl text-paper/60 hover:text-paper text-sm font-medium">
                      Back
                    </button>
                    <button type="submit" disabled={busy}
                      className="flex-1 bg-coral text-paper font-semibold rounded-xl py-2.5 text-sm
                                 hover:bg-coral-dark transition-colors disabled:opacity-50 active:scale-95">
                      {busy ? 'Creating…' : 'Confirm & create account'}
                    </button>
                  </div>
                  <button type="button" disabled={busy || newChildCooldown > 0} onClick={handleResendNewChildCode}
                    className="text-paper/40 hover:text-paper/60 text-xs font-medium disabled:opacity-40">
                    {newChildCooldown > 0 ? `Resend code in ${newChildCooldown}s` : 'Resend code'}
                  </button>
                </form>
              )
            ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              {mode === 'register' && (
                <>
                  <p className="text-paper/40 text-xs leading-relaxed px-1">
                    Ask your child's therapist for their player code — it looks something like
                    <span className="text-paper/60 font-medium"> CHICK42</span>. Entering it here
                    connects your account to your child's, so you can see their progress.
                  </p>
                  <Field icon={KeyRound} type="text" required
                    placeholder="Child's player code"
                    value={form.code} onChange={update('code')} />

                  <GoogleAuthButton
                    onIdToken={handleGoogle}
                    onError={setError}
                    disabled={busy || !form.code.trim()}
                  />
                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-px bg-white/10" />
                    <span className="text-paper/30 text-xs font-medium">or set a password</span>
                    <div className="flex-1 h-px bg-white/10" />
                  </div>

                  <Field icon={User} type="text" placeholder="Your name (optional)" autoComplete="name"
                    value={form.fullName} onChange={update('fullName')} />
                  <Field icon={Phone} type="tel" autoComplete="tel"
                    placeholder="Phone (optional)"
                    value={form.phone} onChange={update('phone')} />
                </>
              )}
              <Field icon={Mail} type="email" required placeholder="Email" autoComplete="email"
                value={form.email} onChange={update('email')} />
              <Field
                icon={Lock}
                type={showPassword ? 'text' : 'password'}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                required
                autoFocus={resumedAfterVerify}
                placeholder="Password"
                value={form.password}
                onChange={update('password')}
                rightElement={
                  <button type="button" onClick={() => setShowPassword(s => !s)}
                          className="text-paper/30 hover:text-paper/60 transition-colors">
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                }
              />

              {error && (
                <div className="bg-coral/10 border border-coral/30 rounded-xl px-4 py-3 text-coral-light text-sm">
                  {error}
                </div>
              )}

              {mode === 'login' && (
                <button
                  type="button"
                  onClick={() => { setShowRecovery((s) => !s); setRecoveryStatus(''); setShowForgotPassword(false); setError('') }}
                  className="text-paper/40 hover:text-paper/60 text-xs font-medium text-left -mt-2 transition-colors"
                >
                  Forgot your child's player code?
                </button>
              )}

              {mode === 'login' && (
                <button
                  type="button"
                  onClick={() => { setShowForgotPassword((s) => !s); resetForgotPasswordFlow(); setShowRecovery(false); setError('') }}
                  className="text-paper/40 hover:text-paper/60 text-xs font-medium text-left"
                >
                  Forgot your password?
                </button>
              )}

              <button type="submit" disabled={busy}
                className="w-full bg-coral text-paper font-semibold rounded-xl py-3 mt-2
                           hover:bg-coral-dark transition-colors disabled:opacity-50 active:scale-95">
                {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
              </button>
            </form>
            )}

            {mode === 'login' && showRecovery && (
              <form onSubmit={handleForgotPlayerCode} className="mt-4 pt-4 border-t border-white/10 flex flex-col gap-3">
                {recoveryStatus === 'sent' ? (
                  <p className="text-paper/50 text-sm">
                    If that email has a linked account, we've sent the player code to it.
                  </p>
                ) : (
                  <>
                    <p className="text-paper/40 text-xs">
                      Enter the email you signed up with and we'll send your child's player code.
                    </p>
                    <Field
                      icon={Mail}
                      type="email"
                      required
                      placeholder="Your email"
                      value={recoveryEmail}
                      onChange={(e) => setRecoveryEmail(e.target.value)}
                    />
                    <button
                      type="submit"
                      disabled={recoveryStatus === 'sending'}
                      className="w-full bg-white/5 text-paper/80 font-medium rounded-xl py-2.5 text-sm
                                 hover:bg-white/10 transition-colors disabled:opacity-50"
                    >
                      {recoveryStatus === 'sending' ? 'Sending…' : 'Send player code'}
                    </button>
                  </>
                )}
              </form>
            )}

            {mode === 'login' && showForgotPassword && (
              <div className="mt-4 pt-4 border-t border-white/10 flex flex-col gap-3">
                {forgotStep === 'request' && (
                  <form onSubmit={handleForgotPasswordSendCode} className="flex flex-col gap-3">
                    <p className="text-paper/40 text-xs">
                      Enter your email and we'll send you a code to reset your password.
                    </p>
                    <Field icon={Mail} type="email" required placeholder="Your email"
                      value={forgotEmail} onChange={(e) => setForgotEmail(e.target.value)} />
                    {forgotError && <p className="text-coral-light text-xs">{forgotError}</p>}
                    <button type="submit" disabled={forgotBusy}
                      className="w-full bg-white/5 text-paper/80 font-medium rounded-xl py-2.5 text-sm
                                 hover:bg-white/10 transition-colors disabled:opacity-50">
                      {forgotBusy ? 'Sending…' : 'Send code'}
                    </button>
                  </form>
                )}

                {forgotStep === 'verify' && (
                  <form onSubmit={handleForgotPasswordConfirm} className="flex flex-col gap-3">
                    <p className="text-paper/40 text-xs">
                      Enter the 6-digit code we emailed you, plus a new password.
                    </p>
                    <Field type="text" required placeholder="6-digit code" value={forgotCode}
                      onChange={(e) => setForgotCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      icon={KeyRound} />
                    <Field icon={Lock} type="password" required placeholder="New password"
                      value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
                    {forgotError && <p className="text-coral-light text-xs">{forgotError}</p>}
                    {forgotResendMsg && <p className="text-paper/50 text-xs">{forgotResendMsg}</p>}
                    <button type="submit" disabled={forgotBusy}
                      className="w-full bg-white/5 text-paper/80 font-medium rounded-xl py-2.5 text-sm
                                 hover:bg-white/10 transition-colors disabled:opacity-50">
                      {forgotBusy ? 'Resetting…' : 'Reset password'}
                    </button>
                    <button type="button" onClick={handleForgotPasswordResend} disabled={forgotBusy || forgotCooldown > 0}
                      className="text-paper/40 hover:text-paper/60 text-xs font-medium transition-colors disabled:opacity-50">
                      {forgotCooldown > 0 ? `Resend code (${forgotCooldown}s)` : 'Resend code'}
                    </button>
                  </form>
                )}

                {forgotStep === 'done' && (
                  <div className="flex flex-col gap-2">
                    <p className="text-paper/50 text-sm">Password reset! Sign in with your new password.</p>
                    <button type="button" onClick={() => { setShowForgotPassword(false); resetForgotPasswordFlow() }}
                      className="text-paper/40 hover:text-paper/60 text-xs font-medium text-left transition-colors">
                      Back to sign in
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          <p className="text-center text-paper/25 text-xs mt-6">
            Only you and your child's therapist can see their progress.
          </p>
        </div>
      </div>
    </div>
  )
}

export default function ParentAuth() {
  return (
    <SavedProfilesGate role="parent">
      <ParentAuthForm />
    </SavedProfilesGate>
  )
}
