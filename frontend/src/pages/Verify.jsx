import { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { verifyAPI, getErrorMessage } from '../api/client'

// Full-page email-OTP gate. Reached from PlaySelect after picking a role
// (?dest=/play | /therapist/login | /parent/login), or from a flow that
// already knows the email (?dest=...&email=...) -- e.g. ParentAuth's
// new-child registration, which hits a 403 needing email consent and
// sends the parent here with their email already typed in. When `email`
// is present we skip the "what's your email" step entirely and fire the
// code request automatically, since asking them to retype what they just
// typed would be a pointless extra step. On success, navigates to `dest`
// regardless of first_time -- the destination itself (kid login,
// therapist login, parent login) is where real identity gets established;
// this just proves the email is real before any of that.
export default function Verify() {
  const [searchParams] = useSearchParams()
  const dest = searchParams.get('dest') || '/play-select'
  const emailParam = searchParams.get('email') || ''
  const navigate = useNavigate()

  const [step, setStep] = useState('email') // 'email' | 'code'
  const [email, setEmail] = useState(() => emailParam || localStorage.getItem('bq_verified_email') || '')
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [cooldown, setCooldown] = useState(0)
  const autoSentRef = useRef(false)

  // Resend cooldown -- ticks down once a second whenever cooldown > 0.
  // Prevents spamming the "Resend code" button, which would otherwise
  // hammer the email-send endpoint with no feedback that anything's
  // actually happening.
  useEffect(() => {
    if (cooldown <= 0) return
    const t = setInterval(() => setCooldown((c) => Math.max(0, c - 1)), 1000)
    return () => clearInterval(t)
  }, [cooldown])

  async function requestCode(targetEmail) {
    setError('')
    setLoading(true)
    try {
      await verifyAPI.request({ email: targetEmail })
      setStep('code')
      setCooldown(30)
    } catch (err) {
      setError(getErrorMessage(err, "Couldn't send code — try again"))
      // If the auto-send failed, fall back to showing the email step so
      // the parent isn't stuck on a dead end with no way to retry.
      setStep('email')
    } finally {
      setLoading(false)
    }
  }

  // Auto-send when we arrived with a known email -- only once, so a
  // failed send (which falls back to 'email' step above) doesn't loop.
  useEffect(() => {
    if (emailParam && !autoSentRef.current) {
      autoSentRef.current = true
      requestCode(emailParam)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [emailParam])

  async function handleRequestCode(e) {
    e.preventDefault()
    requestCode(email)
  }

  async function handleConfirmCode(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await verifyAPI.confirm({ email, code })
      // Remember this device already proved this email, so PlaySelect's
      // routeFor() can skip the /verify hop next time -- without this,
      // every single visit to /play-select (logout, back button, closing
      // and reopening the tab) re-triggers the full email-OTP round trip,
      // even though nothing about the email changed.
      localStorage.setItem('bq_verified_email', email)
      navigate(dest)
    } catch (err) {
      setError(getErrorMessage(err, 'Incorrect code — try again'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-6 py-16"
      style={{
        background: 'linear-gradient(180deg, #12142E 0%, #241F49 38%, #6B4A8A 78%, #9A5F72 100%)',
      }}
    >
      <div className="w-full max-w-sm rounded-[2rem] p-8 bg-dusk-mid/60 backdrop-blur-sm border-2 border-ember/25">
        {step === 'email' && (
          <form onSubmit={handleRequestCode}>
            <h1 className="font-vm-display text-2xl font-bold text-paper mb-2">What's your email?</h1>
            <p className="text-paper/50 text-sm mb-5">We'll send a quick code to make sure it's really you.</p>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-xl px-4 py-3 bg-white/10 text-paper placeholder-paper/30 mb-3 outline-none focus:ring-2 focus:ring-ember/50"
            />
            {error && <p className="text-coral-light text-sm mb-3">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl py-3 bg-ember/80 hover:bg-ember text-dusk-mid font-bold disabled:opacity-50 transition-colors"
            >
              {loading ? 'Sending…' : 'Send code'}
            </button>
            <button
              type="button"
              onClick={() => navigate('/play-select')}
              className="w-full text-paper/40 text-sm mt-4"
            >
              ← Back
            </button>
          </form>
        )}

        {step === 'code' && (
          <form onSubmit={handleConfirmCode}>
            <h1 className="font-vm-display text-2xl font-bold text-paper mb-2">Enter your code</h1>
            <p className="text-paper/50 text-sm mb-1">Sent to {email} — check your inbox.</p>
            <p className="text-paper/40 text-xs mb-5">
              Don't see it? Check your spam/junk folder — verification emails sometimes land there.
              It can also take a minute or two to arrive.
            </p>
            <input
              type="text"
              required
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              placeholder="123456"
              className="w-full rounded-xl px-4 py-3 bg-white/10 text-paper placeholder-paper/30 mb-3 outline-none focus:ring-2 focus:ring-ember/50 tracking-widest text-center text-lg"
            />
            {error && <p className="text-coral-light text-sm mb-3">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl py-3 bg-ember/80 hover:bg-ember text-dusk-mid font-bold disabled:opacity-50 transition-colors"
            >
              {loading ? 'Checking…' : 'Confirm'}
            </button>
            <button
              type="button"
              onClick={() => requestCode(email)}
              disabled={loading || cooldown > 0}
              className="w-full text-paper/50 text-sm mt-3 disabled:opacity-50"
            >
              {cooldown > 0 ? `Resend code (${cooldown}s)` : "Didn't get it? Resend code"}
            </button>
            <button
              type="button"
              onClick={() => { setStep('email'); setCode(''); setError('') }}
              className="w-full text-paper/40 text-sm mt-2"
            >
              Wrong email? Go back
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
