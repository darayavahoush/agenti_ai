import { useState, useEffect } from 'react'
import { dashboardAPI, patientsAPI } from '../api/breathquestClient'

export default function BreathQuestTherapistDashboard({ setPage }) {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [search, setSearch] = useState('')
  const [therapistName, setTherapistName] = useState('')

  useEffect(() => {
    // Load therapist name from localStorage
    const name = localStorage.getItem('bq_therapist_name') || 'Therapist'
    setTherapistName(name)
    
    // Load dashboard data
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const [summaryResponse, patientsResponse] = await Promise.all([
        dashboardAPI.summary(),
        patientsAPI.list()
      ])
      
      setSummary({
        ...summaryResponse.data,
        patients: patientsResponse.data || []
      })
    } catch (err) {
      console.error('Failed to load dashboard data:', err)
      // Set empty data on error
      setSummary({
        total_patients: 0,
        active_patients: 0,
        sessions_this_week: 0,
        avg_stars_this_week: 0,
        patients: []
      })
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('bq_token')
    localStorage.removeItem('bq_therapist_id')
    localStorage.removeItem('bq_therapist_name')
    setPage('breathquest-landing')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#12122A' }}>
        <div className="text-white text-xl">Loading...</div>
      </div>
    )
  }

  const patients = (summary?.patients || []).filter(p =>
    p.first_name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="min-h-screen" style={{ background: '#12122A' }}>
      {/* Top nav */}
      <nav className="border-b border-white/10 px-6 py-4 flex items-center justify-between sticky top-0 bg-[#12122A]/95 backdrop-blur z-10">
        <div className="flex items-center gap-3">
          <span className="text-2xl">💨</span>
          <span className="text-xl font-bold text-white" style={{ fontFamily: 'sans-serif' }}>
            Breath<span className="text-green-400">Quest</span>
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-white/50 text-sm">{therapistName}</span>
          <button 
            onClick={handleLogout}
            className="text-white/50 hover:text-white text-sm transition-colors"
          >
            Sign out
          </button>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white" style={{ fontFamily: 'sans-serif' }}>Dashboard</h1>
            <p className="text-white/40 mt-1">Welcome back, {therapistName}</p>
          </div>
          <button 
            onClick={() => setShowAdd(true)}
            className="px-6 py-3 rounded-xl font-bold bg-green-400 hover:bg-green-500 text-black transition-all"
          >
            + Add Patient
          </button>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Total Patients',    value: summary?.total_patients ?? 0, icon: '👥', color: 'text-green-400' },
            { label: 'Active Patients',   value: summary?.active_patients ?? 0, icon: '✅', color: 'text-teal-400' },
            { label: 'Sessions This Week',value: summary?.sessions_this_week ?? 0, icon: '🎮', color: 'text-amber-400' },
            { label: 'Avg Accuracy',      value: summary?.avg_accuracy_this_week != null
                ? `${summary.avg_accuracy_this_week.toFixed(1)}%` : '—',           icon: '🎯', color: 'text-purple-400' },
          ].map(({ label, value, icon, color }) => (
            <div key={label} className="bg-white/5 border border-white/10 rounded-2xl p-4 flex flex-col gap-1">
              <span className="text-2xl">{icon}</span>
              <span className={`text-2xl font-bold ${color}`} style={{ fontFamily: 'sans-serif' }}>{value}</span>
              <span className="text-white/40 text-xs">{label}</span>
            </div>
          ))}
        </div>

        {/* Patient list */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Patients</h2>
          <input
            className="w-64 p-2 rounded-xl bg-white/10 border border-white/20 text-white text-sm focus:outline-none focus:border-green-400"
            placeholder="Search patients…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        {patients.length === 0 ? (
          <div className="bg-white/5 border border-white/10 rounded-2xl text-center py-16">
            <div className="text-5xl mb-4">🌱</div>
            <p className="text-white/50">No patients yet — add your first one!</p>
            <button 
              className="mt-4 px-6 py-3 rounded-xl font-bold bg-green-400 hover:bg-green-500 text-black transition-all"
              onClick={() => setShowAdd(true)}
            >
              Add Patient
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {patients.map(p => (
              <PatientCard key={p.id} patient={p} />
            ))}
          </div>
        )}
      </div>

      {showAdd && (
        <AddPatientModal 
          onClose={() => setShowAdd(false)}
          onAdd={loadDashboardData}
        />
      )}
    </div>
  )
}

function PatientCard({ patient }) {
  const starsColor = patient.total_stars >= 12 ? 'green'
                   : patient.total_stars >= 6  ? 'amber'
                   : 'gray'
  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-4 text-left hover:border-green-400/40 hover:bg-green-400/5 transition-all duration-200 hover:scale-[1.02] group w-full">
      <div className="flex items-center gap-3 mb-4">
        <div className="text-4xl">
          {patient.avatar === 'chick' ? '🐥' : 
           patient.avatar === 'dragon' ? '🐉' :
           patient.avatar === 'cloud' ? '☁️' :
           patient.avatar === 'star' ? '⭐' :
           patient.avatar === 'rocket' ? '🚀' : '🐠'}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-white truncate">{patient.first_name}</p>
          {patient.age && <p className="text-white/40 text-xs">Age {patient.age}</p>}
        </div>
        <span className={`px-2 py-1 rounded-full text-xs font-bold ${
          patient.is_active ? 'bg-green-400/20 text-green-400' : 'bg-gray-400/20 text-gray-400'
        }`}>
          {patient.is_active ? 'Active' : 'Inactive'}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3 text-center">
        <div>
          <p className="text-lg font-bold text-amber-400">{patient.total_sessions}</p>
          <p className="text-white/30 text-xs">sessions</p>
        </div>
        <div>
          <p className="text-lg font-bold text-yellow-400">{patient.total_stars}</p>
          <p className="text-white/30 text-xs">stars</p>
        </div>
        <div>
          <p className="text-lg font-bold text-green-400">
            {patient.last_session_at
              ? new Date(patient.last_session_at).toLocaleDateString('en', { month: 'short', day: 'numeric' })
              : '—'}
          </p>
          <p className="text-white/30 text-xs">last session</p>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-white/5 flex items-center justify-between">
        <span className="text-white/30 text-xs">View progress</span>
        <span className="text-green-400 text-xs group-hover:translate-x-1 transition-transform">→</span>
      </div>
    </div>
  )
}

function AddPatientModal({ onClose, onAdd }) {
  const [form, setForm] = useState({ first_name: '', age: '', avatar: 'chick' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    
    try {
      await patientsAPI.create({
        first_name: form.first_name,
        age: parseInt(form.age) || null,
        avatar: form.avatar
      })
      onAdd()
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add patient')
    } finally {
      setLoading(false)
    }
  }

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-[#1a1a2e] border border-white/10 rounded-2xl p-6 w-full max-w-md">
        <h2 className="text-2xl font-bold text-white mb-4" style={{ fontFamily: 'sans-serif' }}>Add New Patient</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="text-sm text-white/50 block mb-1">First Name</label>
            <input 
              className="w-full p-3 rounded-xl bg-white/10 border border-white/20 text-white focus:outline-none focus:border-green-400" 
              placeholder="e.g. Alex"
              value={form.first_name}
              onChange={set('first_name')}
              required
            />
          </div>
          <div>
            <label className="text-sm text-white/50 block mb-1">Age</label>
            <input 
              className="w-full p-3 rounded-xl bg-white/10 border border-white/20 text-white focus:outline-none focus:border-green-400" 
              type="number" 
              placeholder="e.g. 8"
              value={form.age}
              onChange={set('age')}
              required
            />
          </div>
          <div>
            <label className="text-sm text-white/50 block mb-1">Avatar</label>
            <select 
              className="w-full p-3 rounded-xl bg-white/10 border border-white/20 text-white focus:outline-none focus:border-green-400"
              value={form.avatar}
              onChange={set('avatar')}
            >
              <option value="chick">🐥 Chick</option>
              <option value="dragon">🐉 Dragon</option>
              <option value="cloud">☁️ Cloud</option>
              <option value="star">⭐ Star</option>
              <option value="rocket">🚀 Rocket</option>
            </select>
          </div>
          {error && (
            <div className="bg-orange-400/10 border border-orange-400/30 rounded-xl px-4 py-3 text-orange-400 text-sm">
              {error}
            </div>
          )}
          <div className="flex gap-3 mt-4">
            <button 
              type="button"
              onClick={onClose}
              className="flex-1 px-6 py-3 rounded-xl font-bold bg-white/10 text-white hover:bg-white/20 transition-all"
            >
              Cancel
            </button>
            <button 
              type="submit"
              disabled={loading}
              className="flex-1 px-6 py-3 rounded-xl font-bold bg-green-400 hover:bg-green-500 text-black transition-all disabled:opacity-50"
            >
              {loading ? 'Adding...' : 'Add Patient'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
