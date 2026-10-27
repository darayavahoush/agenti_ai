import { useCallback, useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const BASE = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '')
const API = BASE + '/admin'
const TK = 'admin_token'
const COLORS = { kid: '#6366f1', parent: '#10b981', therapist: '#f59e0b' }

async function call(path, token, opts = {}) {
  const res = await fetch(API + path, {
    ...opts,
    headers: { 'content-type': 'application/json', ...(token ? { authorization: `Bearer ${token}` } : {}) },
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw Object.assign(new Error(body.detail || 'Request failed'), { status: res.status })
  return body
}

function Login({ onToken }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setErr('')
    try {
      const r = await call('/login', null, { method: 'POST', body: JSON.stringify({ email, password }) })
      sessionStorage.setItem(TK, r.access_token)
      onToken(r.access_token)
    } catch (ex) { setErr(ex.message) } finally { setBusy(false) }
  }
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <form onSubmit={submit} className="bg-white p-8 rounded-xl shadow w-full max-w-sm space-y-4">
        <h1 className="text-xl font-semibold">Admin sign in</h1>
        <input className="w-full border rounded px-3 py-2" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="w-full border rounded px-3 py-2" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {err && <p className="text-sm text-red-600">{err}</p>}
        <button disabled={busy} className="w-full bg-indigo-600 text-white rounded py-2 disabled:opacity-50">{busy ? 'Signing in…' : 'Sign in'}</button>
      </form>
    </div>
  )
}

const Card = ({ label, value }) => (
  <div className="bg-white rounded-xl shadow p-4">
    <div className="text-sm text-gray-500">{label}</div>
    <div className="text-2xl font-semibold">{value}</div>
  </div>
)

function Dashboard({ token, onLogout }) {
  const [days, setDays] = useState(7)
  const [m, setM] = useState(null)
  const [summaries, setSummaries] = useState([])
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const guard = useCallback((ex) => {
    if (ex.status === 401) onLogout()
    else setErr(ex.message)
  }, [onLogout])

  useEffect(() => {
    setErr('')
    call(`/metrics?days=${days}`, token).then(setM).catch(guard)
  }, [days, token, guard])
  useEffect(() => { call('/summaries', token).then(setSummaries).catch(guard) }, [token, guard])

  const generate = async () => {
    setBusy(true); setErr('')
    try {
      await call(`/summary?days=${days}`, token, { method: 'POST' })
      setSummaries(await call('/summaries', token))
    } catch (ex) { guard(ex) } finally { setBusy(false) }
  }

  const byDate = {}
  ;(m?.daily_active_users || []).forEach((r) => {
    byDate[r.date] = byDate[r.date] || { date: r.date.slice(5) }
    byDate[r.date][r.user_type] = r.active_users
  })
  const chart = Object.values(byDate)
  const sum = (k) => Object.values(m?.logins || {}).reduce((a, v) => a + (v[k] || 0), 0)

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <div className="flex gap-3 items-center">
            <select className="border rounded px-2 py-1" value={days} onChange={(e) => setDays(Number(e.target.value))}>
              <option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option>
            </select>
            <button onClick={onLogout} className="text-sm text-gray-600 underline">Sign out</button>
          </div>
        </div>
        {err && <p className="text-red-600 text-sm">{err}</p>}
        {m && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card label="Successful logins" value={sum('success')} />
              <Card label="Failed logins" value={sum('failed')} />
              <Card label="Revenue (INR)" value={`₹${m.revenue_inr.toFixed(2)}`} />
              <Card label="Failed payments" value={m.payments_by_state.failed?.count || 0} />
            </div>
            <div className="bg-white rounded-xl shadow p-4">
              <h2 className="font-medium mb-2">Daily active users</h2>
              {chart.length ? (
                <div style={{ height: 260 }}>
                  <ResponsiveContainer>
                    <BarChart data={chart}>
                      <XAxis dataKey="date" /><YAxis allowDecimals={false} /><Tooltip /><Legend />
                      {Object.keys(COLORS).map((k) => <Bar key={k} dataKey={k} stackId="a" fill={COLORS[k]} />)}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : <p className="text-sm text-gray-500">No activity in this window yet.</p>}
            </div>
            <div className="bg-white rounded-xl shadow p-4">
              <h2 className="font-medium mb-2">Failed payments</h2>
              {m.failed_payments.length ? (
                <table className="w-full text-sm">
                  <thead><tr className="text-left text-gray-500"><th>When</th><th>Who</th><th>Plan</th><th>₹</th><th>Reason</th></tr></thead>
                  <tbody>{m.failed_payments.map((p) => (
                    <tr key={p.merchant_order_id} className="border-t">
                      <td>{p.created_at.slice(0, 16).replace('T', ' ')}</td><td>{p.owner_kind}</td><td>{p.plan_type}</td>
                      <td>{(p.amount_paise / 100).toFixed(2)}</td><td>{p.failure_reason || '—'}</td>
                    </tr>
                  ))}</tbody>
                </table>
              ) : <p className="text-sm text-gray-500">None.</p>}
            </div>
          </>
        )}
        <div className="bg-white rounded-xl shadow p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-medium">AI summary</h2>
            <button onClick={generate} disabled={busy} className="bg-indigo-600 text-white rounded px-3 py-1 text-sm disabled:opacity-50">
              {busy ? 'Generating…' : 'Generate summary'}
            </button>
          </div>
          {summaries.length === 0 && <p className="text-sm text-gray-500">No summaries yet.</p>}
          {summaries.map((s) => (
            <div key={s.id} className="border-t pt-2">
              <div className="text-xs text-gray-500">{s.created_at.slice(0, 16).replace('T', ' ')} UTC</div>
              <p className="text-sm whitespace-pre-wrap">{s.text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function AdminDashboard() {
  const [token, setToken] = useState(() => sessionStorage.getItem(TK))
  const logout = useCallback(() => { sessionStorage.removeItem(TK); setToken(null) }, [])
  return token ? <Dashboard token={token} onLogout={logout} /> : <Login onToken={setToken} />
}
