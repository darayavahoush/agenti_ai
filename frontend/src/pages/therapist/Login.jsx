import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { getErrorMessage, authAPI, verifyAPI } from '../../api/client'
import { Button, Input, Card } from '../../components/ui'
import GoogleAuthButton from '../../components/ui/GoogleAuthButton'
import {
  ClipboardList, LineChart, ShieldCheck,
  Mail, Lock, User, Building2, Phone, Eye, EyeOff, ArrowLeft, Stethoscope,
} from 'lucide-react'

const VALUE_PROPS = [
  { icon: ClipboardList, text: 'Assign exercises and track every session in one place' },
  { icon: LineChart, text: 'See progress trends across all your patients at a glance' },
  { icon: ShieldCheck, text: "Each patient links only to their own teacher — nothing shared" },
]

export default function TherapistLogin() {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ email: '', password: '', full_name: '', clinic_name: '', phone: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { loginTherapist, registerTherapist, loginTherapistGoogle } = useAuth()
  const navigate = useNavigate()

  // Forgot-password: request -> verify. Same OTP round-trip as forgot-PIN
  // in Play.jsx (verifyAPI.request/.confirm), then reset in the same call
  // that confirms the code.
  const [forgotStep, setForgotStep] = useState('request') // request | verify | done
  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotCode, setForgotCode] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [resendMsg, setResendMsg] = useState('')
  const [resendCooldown, setResendCooldown] = useState(0)

  useEffect(() => {
    if (resendCooldown <= 0) return
    const t = setInterval(() => setResendCooldown((c) => Math.max(0, c - 1)), 1000)
    return () => clearInterval(t)
  }, [resendCooldown])

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))

  const resetForgotFlow = () => {
    setForgotStep('request'); setForgotEmail(''); setForgotCode('')
    setNewPassword(''); setError(''); setResendMsg(''); setResendCooldown(0)
  }

  const handleForgotSendCode = async () => {
    if (!forgotEmail.trim()) { setError('Enter your email'); return }
    setError(''); setResendMsg(''); setLoading(true)
    try {
      await verifyAPI.request({ email: forgotEmail.trim() })
      setForgotStep('verify')
      setResendCooldown(30)
    } catch (e) {
      setError(getErrorMessage(e, "Couldn't send the code — try again"))
    } finally {
      setLoading(false)
    }
  }

  const handleForgotResend = async () => {
    setError(''); setResendMsg(''); setLoading(true)
    try {
      await verifyAPI.request({ email: forgotEmail.trim() })
      setResendMsg('Code resent!')
      setResendCooldown(30)
    } catch (e) {
      setError(getErrorMessage(e, "Couldn't resend the code — try again"))
    } finally {
      setLoading(false)
    }
  }

  const handleForgotConfirm = async () => {
    if (forgotCode.trim().length !== 6) { setError('Enter the 6-digit code'); return }
    if (newPassword.length < 8)         { setError('Password must be at least 8 characters'); return }
    setError(''); setLoading(true)
    try {
      await verifyAPI.confirm({ email: forgotEmail.trim(), code: forgotCode.trim() })
    } catch (e) {
      setError(getErrorMessage(e, "That code didn't work — try again"))
      setLoading(false)
      return
    }
    try {
      await authAPI.therapistResetPassword({ email: forgotEmail.trim(), new_password: newPassword })
      setForgotStep('done')
    } catch (e) {
      setError(getErrorMessage(e, "Couldn't reset the password — try again"))
    } finally {
      setLoading(false)
    }
  }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        await loginTherapist(form.email, form.password)
      } else {
        await registerTherapist(form)
      }
      navigate('/therapist/dashboard')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const submitGoogle = async (idToken) => {
    setError('')
    setLoading(true)
    try {
      await loginTherapistGoogle(idToken)
      navigate('/therapist/dashboard')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2" style={{ background: '#0F1D22' }}>

      <div className="hidden lg:flex flex-col justify-center px-16 relative overflow-hidden"
           style={{ background: 'radial-gradient(ellipse at 30% 20%, #1E8C7D 0%, #12222A 55%, #0F1D22 100%)' }}>
        <div className="absolute -top-24 -left-24 w-72 h-72 rounded-full bg-mint/10 blur-3xl" />
        <div className="absolute bottom-0 right-0 w-96 h-96 rounded-full bg-mint-dark/10 blur-3xl" />

        <div className="relative z-10 max-w-sm">
          <div className="w-14 h-14 rounded-2xl bg-mint/15 border border-mint/25 flex items-center justify-center mb-8">
            <Stethoscope className="w-7 h-7 text-mint-light" />
          </div>
          <h1 className="font-vm-display text-4xl font-bold text-paper leading-tight mb-4">
            Everything your patients practice, in one dashboard.
          </h1>
          <p className="text-paper/50 mb-10">
            BreathQuest links each kid's play directly to your caseload — no separate logins to juggle.
          </p>

          <div className="flex flex-col gap-5">
            {VALUE_PROPS.map(({ icon: Icon, text }, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-mint/10 border border-mint/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Icon className="w-4 h-4 text-mint-light" />
                </div>
                <p className="text-paper/70 text-sm leading-relaxed pt-1">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-center p-6 py-16">
        <div className="w-full max-w-md">
          <Link to="/" className="inline-flex items-center gap-2 text-white/50 hover:text-white
                                  hover:bg-white/5 transition-colors mb-8 text-sm font-medium
                                  -ml-3 px-3 py-1.5 rounded-full">
            <ArrowLeft className="w-4 h-4" /> Back
          </Link>

          <div className="mb-8 lg:hidden text-center">
            <div className="w-14 h-14 rounded-2xl bg-mint/15 border border-mint/25 flex items-center justify-center mx-auto mb-4">
              <Stethoscope className="w-7 h-7 text-mint-light" />
            </div>
            <h1 className="font-vm-display text-2xl font-bold text-white">Teacher Portal</h1>
          </div>

          <div className="mb-6 hidden lg:block">
            <h2 className="font-vm-display text-2xl font-bold text-white">
              {mode === 'login' ? 'Welcome back' : 'Create your account'}
            </h2>
            <p className="text-white/40 text-sm mt-1">
              {mode === 'login' ? 'Sign in to your dashboard' : 'Takes about a minute'}
            </p>
          </div>

          <Card className="border-white/10">
            {mode === 'forgot' ? (
              <>
                <button onClick={() => { setMode('login'); resetForgotFlow() }}
                        className="flex items-center gap-1.5 text-white/40 hover:text-white text-sm mb-5 transition-colors">
                  <ArrowLeft className="w-3.5 h-3.5" /> Back to sign in
                </button>

                {forgotStep === 'request' && (
                  <div className="flex flex-col gap-4">
                    <div>
                      <h3 className="text-white font-semibold mb-1">Reset your password</h3>
                      <p className="text-white/40 text-sm">We'll email you a code to confirm it's you.</p>
                    </div>
                    <Input icon={Mail} label="Email" type="email" placeholder="you@clinic.com" autoComplete="email"
                           value={forgotEmail} onChange={(e) => setForgotEmail(e.target.value)} required />
                    {error && (
                      <div className="bg-brand-coral/10 border border-brand-coral/30 rounded-xl px-4 py-3 text-brand-coral text-sm">
                        {error}
                      </div>
                    )}
                    <Button variant="teal" className="w-full" disabled={loading} onClick={handleForgotSendCode}>
                      {loading ? 'Sending…' : 'Send code'}
                    </Button>
                  </div>
                )}

                {forgotStep === 'verify' && (
                  <div className="flex flex-col gap-4">
                    <div>
                      <h3 className="text-white font-semibold mb-1">Check your email</h3>
                      <p className="text-white/40 text-sm">Enter the 6-digit code and a new password.</p>
                    </div>
                    <Input label="6-digit code" placeholder="123456" autoComplete="one-time-code" inputMode="numeric" value={forgotCode}
                           onChange={(e) => setForgotCode(e.target.value.replace(/\D/g, '').slice(0, 6))} required />
                    <Input icon={Lock} label="New password" type="password" placeholder="••••••••" autoComplete="new-password"
                           value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required />
                    {error && (
                      <div className="bg-brand-coral/10 border border-brand-coral/30 rounded-xl px-4 py-3 text-brand-coral text-sm">
                        {error}
                      </div>
                    )}
                    {resendMsg && <p className="text-mint-light text-sm">{resendMsg}</p>}
                    <Button variant="teal" className="w-full" disabled={loading} onClick={handleForgotConfirm}>
                      {loading ? 'Resetting…' : 'Reset password'}
                    </Button>
                    <button type="button" onClick={handleForgotResend} disabled={loading || resendCooldown > 0}
                            className="text-white/40 hover:text-white text-sm transition-colors disabled:opacity-50">
                      {resendCooldown > 0 ? `Resend code (${resendCooldown}s)` : 'Resend code'}
                    </button>
                  </div>
                )}

                {forgotStep === 'done' && (
                  <div className="flex flex-col gap-4 text-center py-4">
                    <h3 className="text-white font-semibold">Password reset!</h3>
                    <p className="text-white/40 text-sm">Sign in with your new password.</p>
                    <Button variant="teal" className="w-full" onClick={() => { setMode('login'); resetForgotFlow() }}>
                      Back to sign in
                    </Button>
                  </div>
                )}
              </>
            ) : (
            <>
            <div className="flex bg-white/5 rounded-xl p-1 mb-6">
              {['login', 'register'].map(m => (
                <button key={m} onClick={() => { setMode(m); setError('') }}
                  className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all
                    ${mode === m ? 'bg-mint text-brand-dark shadow-sm' : 'text-white/50 hover:text-white'}`}>
                  {m === 'login' ? 'Sign In' : 'Register'}
                </button>
              ))}
            </div>

            {/* Google covers both modes: login-or-register happens
                server-side in one call (see /auth/google's docstring),
                so this button doesn't change with `mode`. */}
            <GoogleAuthButton onIdToken={submitGoogle} onError={setError} disabled={loading} />

            <div className="flex items-center gap-3 my-5">
              <div className="flex-1 h-px bg-white/10" />
              <span className="text-white/30 text-xs font-medium">or</span>
              <div className="flex-1 h-px bg-white/10" />
            </div>

            <form onSubmit={submit} className="flex flex-col gap-4">
              {mode === 'register' && (
                <>
                  <Input icon={User} label="Full name" placeholder="Dr. Jane Smith" autoComplete="name"
                         value={form.full_name} onChange={set('full_name')} required />
                  <Input icon={Building2} label="Clinic name (optional)" placeholder="Happy Kids Clinic" autoComplete="organization"
                         value={form.clinic_name} onChange={set('clinic_name')} />
                  {/* Collected, not verified — no SMS provider wired up yet. */}
                  <Input icon={Phone} label="Phone (optional)" type="tel" placeholder="(555) 123-4567" autoComplete="tel"
                         value={form.phone} onChange={set('phone')} />
                </>
              )}
              <Input icon={Mail} label="Email" type="email" placeholder="you@clinic.com" autoComplete="email"
                     value={form.email} onChange={set('email')} required />

              <Input
                icon={Lock}
                label="Password"
                type={showPassword ? 'text' : 'password'}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                placeholder="••••••••"
                value={form.password}
                onChange={set('password')}
                required
                rightElement={
                  <button type="button" onClick={() => setShowPassword(s => !s)}
                          className="text-white/30 hover:text-white/60 transition-colors">
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                }
              />

              {mode === 'login' && (
                <button type="button" onClick={() => { setMode('forgot'); resetForgotFlow() }}
                        className="text-white/40 hover:text-white text-sm text-left -mt-2 transition-colors">
                  Forgot your password?
                </button>
              )}

              {error && (
                <div className="bg-brand-coral/10 border border-brand-coral/30 rounded-xl px-4 py-3
                                text-brand-coral text-sm">
                  {error}
                </div>
              )}

              <Button type="submit" variant="teal" className="w-full mt-2" disabled={loading}>
                {loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
              </Button>
            </form>
            </>
            )}
          </Card>

          <p className="text-center text-white/25 text-xs mt-6">
            Your patients' data stays linked to your account only.
          </p>
        </div>
      </div>
    </div>
  )
}
