import { useState } from 'react'
import { authAPI } from '../api/breathquestClient'

export default function BreathQuestTherapistLogin({ setPage }) {
  const [mode, setMode]     = useState('login')   // 'login' | 'register'
  const [form, setForm]     = useState({ email: '', password: '', full_name: '', clinic_name: '' })
  const [error, setError]   = useState('')
  const [loading, setLoading] = useState(false)

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    
    try {
      if (mode === 'login') {
        const response = await authAPI.login({ email: form.email, password: form.password })
        localStorage.setItem('bq_token', response.data.access_token)
        localStorage.setItem('bq_therapist_id', response.data.therapist_id)
        localStorage.setItem('bq_therapist_name', response.data.full_name)
      } else {
        const response = await authAPI.register({
          email: form.email,
          password: form.password,
          full_name: form.full_name,
          clinic_name: form.clinic_name || undefined
        })
        localStorage.setItem('bq_token', response.data.access_token)
        localStorage.setItem('bq_therapist_id', response.data.therapist_id)
        localStorage.setItem('bq_therapist_name', response.data.full_name)
      }
      setPage('breathquest-therapist-dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6"
         style={{ background: 'radial-gradient(ellipse at 50% 0%, #1a3a2a 0%, #12122A 60%)' }}>

      <div className="w-full max-w-md">
        <button 
          onClick={() => setPage('breathquest-landing')}
          className="flex items-center gap-2 text-white/40 hover:text-white/70 transition-colors mb-8 text-sm"
        >
          ← Back
        </button>

        <div className="text-center mb-8">
          <div className="text-5xl mb-3">🩺</div>
          <h1 className="text-3xl font-bold text-white" style={{ fontFamily: 'sans-serif' }}>Therapist Portal</h1>
          <p className="text-white/40 mt-1">BreathQuest dashboard</p>
        </div>

        <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
          {/* Toggle */}
          <div className="flex bg-white/5 rounded-xl p-1 mb-6">
            {['login', 'register'].map(m => (
              <button key={m} onClick={() => setMode(m)}
                className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-all
                  ${mode === m ? 'bg-green-400 text-black' : 'text-white/50 hover:text-white'}`}>
                {m === 'login' ? 'Sign In' : 'Register'}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="flex flex-col gap-4">
            {mode === 'register' && (
              <>
                <div>
                  <label className="text-sm text-white/50 block mb-1">Full Name</label>
                  <input className="w-full p-3 rounded-xl bg-white/10 border border-white/20 text-white focus:outline-none focus:border-green-400"
                         placeholder="Dr. Jane Smith"
                         value={form.full_name} onChange={set('full_name')} required />
                </div>
                <div>
                  <label className="text-sm text-white/50 block mb-1">Clinic Name (optional)</label>
                  <input className="w-full p-3 rounded-xl bg-white/10 border border-white/20 text-white focus:outline-none focus:border-green-400"
                         placeholder="Happy Kids Clinic"
                         value={form.clinic_name} onChange={set('clinic_name')} />
                </div>
              </>
            )}
            <div>
              <label className="text-sm text-white/50 block mb-1">Email</label>
              <input className="w-full p-3 rounded-xl bg-white/10 border border-white/20 text-white focus:outline-none focus:border-green-400"
                     type="email" placeholder="you@clinic.com"
                     value={form.email} onChange={set('email')} required />
            </div>
            <div>
              <label className="text-sm text-white/50 block mb-1">Password</label>
              <input className="w-full p-3 rounded-xl bg-white/10 border border-white/20 text-white focus:outline-none focus:border-green-400"
                     type="password" placeholder="••••••••"
                     value={form.password} onChange={set('password')} required />
            </div>

            {error && (
              <div className="bg-orange-400/10 border border-orange-400/30 rounded-xl px-4 py-3 text-orange-400 text-sm">
                {error}
              </div>
            )}

            <button type="submit" className="w-full px-8 py-4 rounded-2xl font-bold text-xl bg-green-400 hover:bg-green-500 text-black transition-all mt-2" 
                    disabled={loading}>
              {loading ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
