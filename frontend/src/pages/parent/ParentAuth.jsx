import { useState, useEffect } from 'react'
import { useNavigate, Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { authAPI, getErrorMessage, verifyAPI } from '../../api/client'
import GoogleAuthButton from '../../components/ui/GoogleAuthButton'
import {
  Heart, LineChart, MessageCircle,
  Mail, Lock, User, KeyRound, Phone, Eye, EyeOff, ArrowLeft,
} from 'lucide-react'

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

export default function ParentAuth() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [sessionExpired] = useState(() => searchParams.get('session_expired') === '1')
  const { loginParent, registerParent, loginParentGoogle, registerParentGoogle } = useAuth()
  const [mode, setMode] = useState('login')
  const [codeType, setCodeType] = useState('player_code')
  const [form, setForm] = useState({ code: '', email: '', password: '', fullName: '', phone: '', kidFirstName: '', kidAvatar: 'chick', kidPin: '' })
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

  // Restore an in-progress new_child registration after the /verify
  // round-trip (see handleSubmit's 403 branch below, which saves this
  // before redirecting). Password is intentionally never persisted here
  // -- see this file's patch-script docstring -- so the parent re-enters
  // just that one field; everything else comes back pre-filled.
  useEffect(() => {
    const raw = localStorage.getItem('bq_pending_parent_kid_register')
    if (!raw) return
    try {
      const pending = JSON.parse(raw)
      setMode('register')
      setCodeType('new_child')
      setForm((f) => ({ ...f, ...pending, password: '' }))
      setResumedAfterVerify(true)
    } catch {
      // Malformed/stale entry -- ignore rather than block the page.
    } finally {
      localStorage.removeItem('bq_pending_parent_kid_register')
    }
  }, [])

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
          code: form.code, codeType, email: form.email, password: form.password,
          fullName: form.fullName, phone: form.phone,
          kidFirstName: form.kidFirstName, kidAvatar: form.kidAvatar, kidPin: form.kidPin,
        })
      }
      localStorage.removeItem('bq_pending_parent_kid_register')
      navigate('/parent/dashboard')
    } catch (err) {
      // A 403 here specifically means parent_kid_register's email-consent
      // gate rejected us (see backend's TEMPORARY 2026-08-28 comment on
      // that route) -- rather than showing a dead-end error, send the
      // parent to the existing /verify page to actually prove the email,
      // then bring them back here to finish registering. Any other error
      // status (400 dup email, 500, network) falls through to the normal
      // inline message instead, since those aren't fixed by verifying.
      if (err?.response?.status === 403 && mode === 'register' && codeType === 'new_child') {
        const { password, ...toPersist } = form
        localStorage.setItem('bq_pending_parent_kid_register', JSON.stringify(toPersist))
        navigate(`/verify?dest=${encodeURIComponent('/auth?role=parent')}&email=${encodeURIComponent(form.email)}`)
        return
      }
      setError(getErrorMessage(err, 'Something went wrong — please try again.'))
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
      setForgotCooldown(30)
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
      setForgotCooldown(30)
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

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              {mode === 'register' && (
                <>
                  {/* Top-level choice: link to an existing child vs. create
                      a brand-new one with no therapist involved. The
                      player_code/invite sub-choice only matters within
                      "existing child", so it's nested below rather than
                      flattened into one 3-way row. */}
                  <div className="flex rounded-full bg-ink p-1 border border-white/10 text-xs font-semibold">
                    <button type="button" onClick={() => setCodeType('player_code')}
                      className={`flex-1 rounded-full py-2 transition-colors ${codeType !== 'new_child' ? 'bg-coral text-paper' : 'text-paper/50'}`}>
                      I have a code
                    </button>
                    <button type="button" onClick={() => setCodeType('new_child')}
                      className={`flex-1 rounded-full py-2 transition-colors ${codeType === 'new_child' ? 'bg-coral text-paper' : 'text-paper/50'}`}>
                      New child, no therapist
                    </button>
                  </div>

                  {codeType === 'new_child' ? (
                    <>
                      <Field icon={User} type="text" required placeholder="Your child's first name"
                        value={form.kidFirstName} onChange={update('kidFirstName')} />
                      <Field icon={KeyRound} type="text" required inputMode="numeric"
                        pattern="\d{4}" maxLength={4} title="PIN must be exactly 4 digits"
                        placeholder="Set a 4-digit PIN for your child"
                        value={form.kidPin}
                        onChange={(e) => setForm((f) => ({ ...f, kidPin: e.target.value.replace(/\D/g, '').slice(0, 4) }))} />
                    </>
                  ) : (
                    <>
                      <p className="text-paper/40 text-xs leading-relaxed px-1">
                        Ask your child's therapist for their player code — it looks something like
                        <span className="text-paper/60 font-medium"> CHICK42</span>. Entering it here
                        connects your account to your child's, so you can see their progress.
                      </p>
                      <Field icon={KeyRound} type="text" required
                        placeholder="Child's player code (e.g. CHICK42)"
                        value={form.code} onChange={update('code')} />

                      {/* Google-register only covers the code-linked path
                          above, not "new child, no therapist" (that one
                          needs phone OTP consent with no Google-auth
                          equivalent yet) -- so the button lives here,
                          gated on a code actually being entered, rather
                          than at the top of the form. */}
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
                    </>
                  )}

                  <Field icon={User} type="text" placeholder="Your name (optional)" autoComplete="name"
                    value={form.fullName} onChange={update('fullName')} />
                  {/* Required for new_child (dual-factor parental consent) --
                      optional otherwise, since no SMS provider is wired up
                      yet for those paths and phone was never enforced. */}
                  <Field icon={Phone} type="tel" required={codeType === 'new_child'} autoComplete="tel"
                    placeholder={codeType === 'new_child' ? 'Your phone number' : 'Phone (optional)'}
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
                  onClick={() => { setShowRecovery((s) => !s); setRecoveryStatus(''); setShowForgotPassword(false) }}
                  className="text-paper/40 hover:text-paper/60 text-xs font-medium text-left -mt-2 transition-colors"
                >
                  Forgot your child's player code?
                </button>
              )}

              {mode === 'login' && (
                <button
                  type="button"
                  onClick={() => { setShowForgotPassword((s) => !s); resetForgotPasswordFlow(); setShowRecovery(false) }}
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
