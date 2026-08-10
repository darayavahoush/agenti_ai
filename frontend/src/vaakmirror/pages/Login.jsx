import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Stethoscope, Smile } from 'lucide-react'
import { Button, Card, Input } from '../../breathquest/components/ui'
import {
  therapistLogin,
  registerTherapist,
  therapistCandidates,
  kidLogin,
  kidRegister,
  kidCandidates
} from '../lib/breathquestApi.js'
import { setAuth } from '../lib/auth.js'

const AVATARS = ['chick', 'dragon', 'cloud', 'star', 'rocket', 'fish']
const AVATAR_EMOJIS = { chick: '🐥', dragon: '🐉', cloud: '☁️', star: '⭐', rocket: '🚀', fish: '🐠' }

export default function Login() {
  // Views: landing | kid-choose | kid-register | kid-login | therapist-login
  const [view, setView] = useState('landing')
  
  // Therapist States
  const [therapistMode, setTherapistMode] = useState('login') // 'login' | 'register'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [clinicName, setClinicName] = useState('')
  const [therapistNames, setTherapistNames] = useState([])
  
  // Kid States
  const [avatar, setAvatar] = useState('chick')
  const [selectedPatientId, setSelectedPatientId] = useState('')
  const [patients, setPatients] = useState([])
  const [playerName, setPlayerName] = useState('')
  const [pin, setPin] = useState('')
  const [registered, setRegistered] = useState(null) // { player_code, first_name }
  
  // General States
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  // Fetch therapist candidates when viewing therapist registration
  useEffect(() => {
    if (view === 'therapist-login' && therapistMode === 'register') {
      therapistCandidates()
        .then((data) => setTherapistNames(data))
        .catch(() => setTherapistNames([]))
    }
  }, [view, therapistMode])

  // Fetch kid candidates when viewing kid registration
  useEffect(() => {
    if (view === 'kid-register') {
      kidCandidates()
        .then((data) => setPatients(data))
        .catch(() => setError('Unable to load registered children. Please try again.'))
    }
  }, [view])

  const handlePin = (digit) => {
    if (pin.length < 4) setPin((p) => p + digit)
  }
  const deletePin = () => setPin((p) => p.slice(0, -1))

  async function handleTherapistLogin(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (therapistMode === 'login') {
        const res = await therapistLogin(email, password)
        setAuth({ kind: 'therapist', token: res.access_token, id: res.therapist_id, name: res.full_name })
        navigate('/vaakmirror/patients')
      } else {
        if (password.length < 8) {
          setError('Password must be at least 8 characters')
          setBusy(false)
          return
        }
        const registerData = {
          email,
          password,
          full_name: fullName,
          clinic_name: clinicName || null
        }
        const res = await registerTherapist(registerData)
        setAuth({ kind: 'therapist', token: res.access_token, id: res.therapist_id, name: res.full_name })
        navigate('/vaakmirror/patients')
      }
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  async function handleKidRegister() {
    if (!selectedPatientId) {
      setError('Choose a registered child')
      return
    }
    if (pin.length < 4) {
      setError('Choose a 4-digit PIN')
      return
    }
    setError('')
    setBusy(true)
    try {
      const data = await kidRegister(selectedPatientId, avatar, pin)
      setRegistered({ player_code: data.player_code, first_name: data.first_name, patient_id: data.patient_id, access_token: data.access_token })
    } catch (e) {
      setError(e.message || 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  async function handleKidLogin() {
    if (!playerName.trim()) {
      setError('Enter your registered name')
      return
    }
    if (pin.length < 4) {
      setError('Enter your PIN')
      return
    }
    setError('')
    setBusy(true)
    try {
      const res = await kidLogin(playerName.trim().toUpperCase(), pin)
      setAuth({
        kind: 'patient',
        token: res.access_token,
        id: res.patient_id,
        name: res.first_name,
        avatar: res.avatar,
      })
      navigate('/vaakmirror')
    } catch (err) {
      setError('Wrong name or PIN — try again!')
      setPin('')
    } finally {
      setBusy(false)
    }
  }

  // --- Show registered player code & PIN info screen ---
  if (registered) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 text-center"
           style={{ background: 'radial-gradient(ellipse at 50% 0%, #1a3a2a 0%, #12122A 60%)' }}>
        <div className="text-7xl mb-4 animate-bounce">{AVATAR_EMOJIS[avatar]}</div>
        <h1 className="font-display text-4xl font-black text-white mb-2">You're in! 🎉</h1>
        <p className="text-white/50 mb-8">Write this down so you can log back in:</p>
        <div className="bg-brand-card border-2 border-brand-green rounded-2xl p-8 mb-6 w-full max-w-xs text-left">
          <p className="text-white/40 text-sm mb-1">Your Player Code</p>
          <p className="font-display text-4xl font-black text-brand-green tracking-widest mb-4">
            {registered.player_code}
          </p>
          <p className="text-white/40 text-sm mb-1">Your PIN</p>
          <p className="font-display text-3xl font-bold text-brand-amber tracking-widest">
            {'•'.repeat(pin.length)}
          </p>
        </div>
        <p className="text-white/30 text-xs mb-8">Show this to your therapist too!</p>
        <Button size="lg" onClick={() => {
          setAuth({
            kind: 'patient',
            token: registered.access_token,
            id: registered.patient_id,
            name: registered.first_name,
            avatar: avatar,
          })
          navigate('/vaakmirror')
        }}>Let's Play! 🚀</Button>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 w-full relative overflow-hidden"
         style={{
           background: view === 'landing' || view === 'therapist-login'
             ? 'radial-gradient(ellipse at 50% 0%, #0E2A2E 0%, #12122A 60%)'
             : 'radial-gradient(ellipse at 50% 0%, #2a1a4a 0%, #12122A 60%)'
         }}>
      
      {/* Background Blurs */}
      <div className="absolute top-20 left-20 w-64 h-64 bg-mint/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-20 right-20 w-64 h-64 bg-brand-purple/5 rounded-full blur-3xl pointer-events-none" />

      {/* Back button */}
      {view !== 'landing' && (
        <button
          onClick={() => { setView('landing'); setError(''); setPin(''); setPlayerName(''); }}
          className="absolute top-6 left-6 text-white/30 hover:text-white/60 text-sm flex items-center gap-1 transition-colors"
        >
          ← Back
        </button>
      )}

      {/* --- 1. LANDING PORTAL SELECT --- */}
      {view === 'landing' && (
        <div className="w-full max-w-lg text-center">
          <div className="text-7xl mb-4 animate-vm-float">✨</div>
          <h1 className="font-display text-5xl font-black text-white mb-2">
            Vaak<span className="text-mint">Mirror</span>
          </h1>
          <p className="text-white/50 text-lg mb-12">Biofeedback articulation exercises</p>

          <div className="flex flex-col sm:flex-row gap-6">
            {/* Kid portal */}
            <button
              onClick={() => setView('kid-choose')}
              className="flex-1 group relative overflow-hidden rounded-3xl p-8 text-center
                         bg-gradient-to-br from-brand-amber/20 to-brand-coral/20
                         border-2 border-brand-amber/30 hover:border-brand-amber/60
                         transition-all duration-300 hover:scale-105 hover:shadow-2xl
                         hover:shadow-brand-amber/20 text-white"
            >
              <div className="text-6xl mb-3 group-hover:animate-bounce">🐥</div>
              <h2 className="font-display text-2xl font-bold text-brand-amber mb-1">I'm a Kid!</h2>
              <p className="text-white/50 text-sm">Play games</p>
              <div className="absolute inset-0 bg-gradient-to-br from-brand-amber/5 to-transparent
                              opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>

            {/* Therapist portal */}
            <button
              onClick={() => setView('therapist-login')}
              className="flex-1 group relative overflow-hidden rounded-3xl p-8 text-center
                         bg-gradient-to-br from-mint/20 to-brand-teal/20
                         border-2 border-mint/30 hover:border-mint/60
                         transition-all duration-300 hover:scale-105 hover:shadow-2xl
                         hover:shadow-mint/20 text-white"
            >
              <div className="text-6xl mb-3 group-hover:animate-bounce">🩺</div>
              <h2 className="font-display text-2xl font-bold text-mint mb-1">Therapist</h2>
              <p className="text-white/50 text-sm">Manage patients</p>
              <div className="absolute inset-0 bg-gradient-to-br from-mint/5 to-transparent
                              opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          </div>
        </div>
      )}

      {/* --- 2. KID CHOOSE FLOW --- */}
      {view === 'kid-choose' && (
        <div className="text-center w-full max-w-sm">
          <div className="text-7xl mb-4 animate-float">🎮</div>
          <h1 className="font-display text-4xl font-black text-white mb-2">VaakMirror</h1>
          <p className="text-white/40 mb-10">Ready to play?</p>
          <div className="flex flex-col gap-4">
            <button
              onClick={() => setView('kid-register')}
              className="p-6 rounded-2xl bg-gradient-to-br from-brand-amber/20 to-brand-coral/20
                         border-2 border-brand-amber/40 hover:border-brand-amber
                         transition-all hover:scale-105 text-left text-white"
            >
              <div className="text-3xl mb-2">✨</div>
              <p className="font-display text-xl font-bold text-white">Set Up PIN</p>
              <p className="text-white/40 text-sm">Choose a registered child</p>
            </button>
            <button
              onClick={() => setView('kid-login')}
              className="p-6 rounded-2xl bg-gradient-to-br from-brand-green/20 to-brand-teal/20
                         border-2 border-brand-green/40 hover:border-brand-green
                         transition-all hover:scale-105 text-left text-white"
            >
              <div className="text-3xl mb-2">🔑</div>
              <p className="font-display text-xl font-bold text-white">I have a code</p>
              <p className="text-white/40 text-sm">Log back in</p>
            </button>
          </div>
        </div>
      )}

      {/* --- 3. KID SETUP PIN / REGISTER --- */}
      {view === 'kid-register' && (
        <div className="w-full max-w-sm">
          <h1 className="font-display text-3xl font-black text-white mb-6 text-center">Set Up Game PIN</h1>

          {/* Registered child */}
          <div className="mb-4 flex flex-col gap-1.5">
            <label className="text-sm text-white/50 block">Choose a registered child</label>
            <select
              className="w-full bg-white/5 border border-white/15 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-brand-green transition-colors text-lg"
              value={selectedPatientId}
              onChange={(e) => setSelectedPatientId(e.target.value)}
            >
              <option value="" className="bg-brand-dark text-white/80">Select a child</option>
              {patients.map((patient) => (
                <option key={patient.id} value={patient.id} className="bg-brand-dark">
                  {patient.name}
                </option>
              ))}
            </select>
            {patients.length === 0 && (
              <p className="text-white/40 text-xs mt-1">No children found. Register the child in Assessment first.</p>
            )}
          </div>

          {/* Avatar selection */}
          <label className="text-sm text-white/50 block mb-2">Pick your character</label>
          <div className="grid grid-cols-6 gap-2 mb-6">
            {AVATARS.map((av) => (
              <button
                key={av}
                onClick={() => setAvatar(av)}
                className={`h-12 rounded-xl text-2xl transition-all border-2 flex items-center justify-center
                  ${avatar === av ? 'border-brand-green bg-brand-green/20 scale-110' : 'border-white/10 bg-white/5'}`}
              >
                {AVATAR_EMOJIS[av]}
              </button>
            ))}
          </div>

          {/* PIN keypad */}
          <label className="text-sm text-white/50 block mb-2 text-center">Choose a 4-digit PIN</label>
          <div className="flex justify-center gap-3 mb-4">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className={`w-5 h-5 rounded-full border-2 transition-all
                  ${pin.length > i ? 'bg-brand-green border-brand-green scale-110 shadow-lg shadow-brand-green/30' : 'border-white/30'}`}
              />
            ))}
          </div>

          <div className="grid grid-cols-3 gap-2 mb-4">
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, '', 0, '⌫'].map((d, i) => (
              <button
                key={i}
                onClick={() => (d === '⌫' ? deletePin() : d !== '' ? handlePin(String(d)) : null)}
                disabled={d === ''}
                className={`h-14 rounded-xl font-display text-xl font-bold transition-all active:scale-95 text-white
                  ${d === '' ? 'invisible' : d === '⌫' ? 'bg-white/5 text-white/50 hover:bg-white/10' : 'bg-white/10 text-white hover:bg-brand-green/20 hover:text-brand-green'}`}
              >
                {d}
              </button>
            ))}
          </div>

          {error && <p className="text-brand-coral text-sm text-center mb-3">{error}</p>}
          <Button className="w-full" size="lg" onClick={handleKidRegister} disabled={busy}>
            {busy ? 'Saving…' : 'Save PIN & Play! 🎉'}
          </Button>
        </div>
      )}

      {/* --- 4. KID LOGIN ("I have a code") --- */}
      {view === 'kid-login' && (
        <div className="w-full max-w-sm">
          <h1 className="font-display text-3xl font-black text-white mb-6 text-center">Welcome Back!</h1>

          <div className="mb-4">
            <Input
              label="Your registered name or player code"
              placeholder="e.g. Alex or P01A2B3C4"
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              className="text-center text-xl font-bold font-display"
            />
          </div>

          <label className="text-sm text-white/50 block mb-2 text-center">Your PIN</label>
          <div className="flex justify-center gap-3 mb-4">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className={`w-5 h-5 rounded-full border-2 transition-all
                  ${pin.length > i ? 'bg-brand-green border-brand-green scale-110 shadow-lg shadow-brand-green/30' : 'border-white/30'}`}
              />
            ))}
          </div>

          <div className="grid grid-cols-3 gap-2 mb-4">
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, '', 0, '⌫'].map((d, i) => (
              <button
                key={i}
                onClick={() => (d === '⌫' ? deletePin() : d !== '' ? handlePin(String(d)) : null)}
                disabled={d === ''}
                className={`h-14 rounded-xl font-display text-xl font-bold transition-all active:scale-95 text-white
                  ${d === '' ? 'invisible' : d === '⌫' ? 'bg-white/5 text-white/50 hover:bg-white/10' : 'bg-white/10 text-white hover:bg-brand-green/20 hover:text-brand-green'}`}
              >
                {d}
              </button>
            ))}
          </div>

          {error && <p className="text-brand-coral text-sm text-center mb-3">{error}</p>}
          <Button className="w-full" size="lg" onClick={handleKidLogin} disabled={busy}>
            {busy ? 'Checking…' : "Let's Play! 🚀"}
          </Button>
        </div>
      )}

      {/* --- 5. THERAPIST LOGIN --- */}
      {view === 'therapist-login' && (
        <Card className="w-full max-w-sm flex flex-col gap-6">
          <div className="text-center">
            <h1 className="font-display text-3xl font-bold text-white">Therapist Portal</h1>
            <p className="text-white/40 text-sm mt-1">Access VaakMirror Dashboard</p>
          </div>

          {/* Toggle */}
          <div className="flex bg-white/5 rounded-xl p-1 mb-2">
            {['login', 'register'].map((m) => (
              <button
                key={m}
                onClick={() => setTherapistMode(m)}
                className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-all
                  ${therapistMode === m ? 'bg-mint text-ink-deep font-bold' : 'text-white/50 hover:text-white'}`}
              >
                {m === 'login' ? 'Sign In' : 'Register'}
              </button>
            ))}
          </div>

          <form onSubmit={handleTherapistLogin} className="flex flex-col gap-4">
            {therapistMode === 'register' && (
              <>
                <Input
                  label="Full Name"
                  placeholder="Start typing therapist name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  list="therapist-names"
                  required
                />
                <datalist id="therapist-names">
                  {therapistNames.map((name) => (
                    <option key={name} value={name} />
                  ))}
                </datalist>
                <Input
                  label="Clinic Name (optional)"
                  placeholder="Happy Kids Clinic"
                  value={clinicName}
                  onChange={(e) => setClinicName(e.target.value)}
                />
              </>
            )}

            <Input
              label="Email Address"
              type="email"
              placeholder="therapist@clinic.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            {error && <p className="text-brand-coral text-sm text-center">{error}</p>}

            <Button type="submit" className="w-full mt-2" size="lg" disabled={busy}>
              {busy ? 'Signing in…' : therapistMode === 'login' ? 'Sign In' : 'Create Account'}
            </Button>
          </form>
        </Card>
      )}
    </div>
  )
}

