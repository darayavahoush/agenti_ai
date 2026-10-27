import { useCallback, useEffect, useMemo, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import './admin.css'

const BASE = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '')
const API = BASE + '/admin'
const TK = 'admin_token'
const ROLES = [
  { key: 'kid', label: 'Kids', color: '#7c83ff' },
  { key: 'parent', label: 'Parents', color: '#34d399' },
  { key: 'therapist', label: 'Therapists', color: '#fbbf24' },
]

async function call(path, token, opts = {}) {
  const res = await fetch(API + path, {
    ...opts,
    headers: { 'content-type': 'application/json', ...(token ? { authorization: `Bearer ${token}` } : {}) },
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw Object.assign(new Error(body.detail || 'Request failed'), { status: res.status })
  return body
}

const P = {
  shield: <><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z" /><path d="M9 12l2 2 4-4" /></>,
  eye: <><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" /></>,
  eyeOff: <><path d="M3 3l18 18" /><path d="M10.6 6.1A9.8 9.8 0 0112 6c6.5 0 10 6 10 6a17 17 0 01-3.2 3.9M6.6 6.7A16.6 16.6 0 002 12s3.5 6 10 6c1.7 0 3.2-.4 4.5-1" /><path d="M9.9 9.9a3 3 0 004.2 4.2" /></>,
  login: <><path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4" /><path d="M10 17l5-5-5-5M15 12H3" /></>,
  alert: <><circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16.5v.01" /></>,
  rupee: <><path d="M6 4h12M6 9h12M6 4c6 0 8 2 8 5s-2 5-8 5l7 6" /></>,
  card: <><rect x="3" y="5" width="18" height="14" rx="2" /><path d="M3 10h18" /></>,
  refresh: <><path d="M20 11a8 8 0 00-14.9-3M4 5v4h4M4 13a8 8 0 0014.9 3M20 19v-4h-4" /></>,
  out: <><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" /><path d="M16 17l5-5-5-5M21 12H9" /></>,
  spark: <><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z" /></>,
}
const Icon = ({ n, style }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={style}>{P[n]}</svg>
)

const when = (iso) => new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
const inr = (v) => '₹' + Number(v).toLocaleString('en-IN', { maximumFractionDigits: 2, minimumFractionDigits: 2 })

function Login({ onToken }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setErr('')
    try {
      const r = await call('/login', null, { method: 'POST', body: JSON.stringify({ email: email.trim(), password }) })
      sessionStorage.setItem(TK, r.access_token)
      onToken(r.access_token)
    } catch (ex) { setErr(ex.message) } finally { setBusy(false) }
  }
  return (
    <div className="adm"><div className="adm-center">
      <form className="adm-login" onSubmit={submit}>
        <div className="adm-mark"><Icon n="shield" /></div>
        <h1>Admin sign in</h1>
        <p className="adm-sub">Vaaksudhi control room. Authorised access only.</p>
        {err && <div className="adm-err"><Icon n="alert" style={{ width: 16, height: 16, flex: 'none' }} />{err}</div>}
        <label className="adm-field"><span>Email</span>
          <div className="adm-input"><input type="email" autoComplete="username" autoFocus placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} required /></div>
        </label>
        <label className="adm-field"><span>Password</span>
          <div className="adm-input">
            <input type={show ? 'text' : 'password'} autoComplete="current-password" placeholder="••••••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required style={{ paddingRight: 44 }} />
            <button type="button" className="adm-eye" onClick={() => setShow(!show)} aria-label="Toggle password"><Icon n={show ? 'eyeOff' : 'eye'} /></button>
          </div>
        </label>
        <button className="adm-btn" disabled={busy}>{busy ? <><span className="adm-spin" />Signing in</> : 'Sign in'}</button>
      </form>
    </div></div>
  )
}

function Kpi({ label, value, sub, icon, color }) {
  return (
    <div className="adm-card adm-kpi">
      <div className="adm-kpi-h"><span>{label}</span>
        <span className="adm-ic" style={{ background: color + '22', color }}><Icon n={icon} /></span></div>
      <div className="adm-kpi-v">{value}</div>
      <div className="adm-kpi-s">{sub}</div>
    </div>
  )
}

const STATE_COLOR = { completed: '#34d399', failed: '#fb7185', pending: '#fbbf24', created: '#8f99b8' }

function Dashboard({ token, onLogout }) {
  const [days, setDays] = useState(7)
  const [m, setM] = useState(null)
  const [sums, setSums] = useState([])
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [tick, setTick] = useState(0)

  const guard = useCallback((ex) => { if (ex.status === 401) onLogout(); else setErr(ex.message) }, [onLogout])

  useEffect(() => {
    setErr(''); setM(null)
    call(`/metrics?days=${days}`, token).then(setM).catch(guard)
  }, [days, token, guard, tick])
  useEffect(() => { call('/summaries', token).then(setSums).catch(guard) }, [token, guard])

  const generate = async () => {
    setBusy(true); setErr('')
    try { await call(`/summary?days=${days}`, token, { method: 'POST' }); setSums(await call('/summaries', token)) }
    catch (ex) { guard(ex) } finally { setBusy(false) }
  }

  const chart = useMemo(() => {
    const rows = {}
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(Date.now() - i * 864e5).toISOString().slice(0, 10)
      rows[d] = { date: d, label: d.slice(5), kid: 0, parent: 0, therapist: 0 }
    }
    ;(m?.daily_active_users || []).forEach((r) => { if (rows[r.date]) rows[r.date][r.user_type] = r.active_users })
    return Object.values(rows)
  }, [m, days])

  const lg = m?.logins || {}
  const ok = Object.values(lg).reduce((a, v) => a + (v.success || 0), 0)
  const bad = Object.values(lg).reduce((a, v) => a + (v.failed || 0), 0)
  const failRate = ok + bad ? Math.round((bad / (ok + bad)) * 100) : 0
  const pay = m?.payments_by_state || {}
  const hasActivity = chart.some((r) => r.kid + r.parent + r.therapist > 0)

  return (
    <div className="adm">
      <header className="adm-top">
        <div className="adm-brand"><div className="adm-mark"><Icon n="shield" /></div>
          <div><b>Vaaksudhi Admin</b><small>Usage and revenue overview</small></div></div>
        <div className="adm-tools">
          <div className="adm-seg">{[7, 30, 90].map((d) => <button key={d} className={d === days ? 'on' : ''} onClick={() => setDays(d)}>{d}d</button>)}</div>
          <button className="adm-ghost" onClick={() => setTick((t) => t + 1)}><Icon n="refresh" />Refresh</button>
          <button className="adm-ghost" onClick={onLogout}><Icon n="out" />Sign out</button>
        </div>
      </header>

      <main className="adm-main">
        {err && <div className="adm-err"><Icon n="alert" style={{ width: 16, height: 16 }} />{err}</div>}

        <section className="adm-kpis">
          {!m ? [0, 1, 2, 3].map((i) => <div key={i} className="adm-sk" style={{ height: 124 }} />) : <>
            <Kpi label="Successful logins" value={ok.toLocaleString('en-IN')} sub={`last ${days} days`} icon="login" color="#7c83ff" />
            <Kpi label="Failed logins" value={bad.toLocaleString('en-IN')} sub={`${failRate}% of all attempts`} icon="alert" color="#fb7185" />
            <Kpi label="Revenue" value={inr(m.revenue_inr)} sub={`${pay.completed?.count || 0} completed payments`} icon="rupee" color="#34d399" />
            <Kpi label="Failed payments" value={pay.failed?.count || 0} sub={`${pay.pending?.count || 0} pending`} icon="card" color="#fbbf24" />
          </>}
        </section>

        <section className="adm-grid2">
          <div className="adm-card">
            <div className="adm-h"><h2>Daily active users</h2>
              <div className="adm-legend">{ROLES.map((r) => <span key={r.key}><i style={{ background: r.color }} />{r.label}</span>)}</div></div>
            {!m ? <div className="adm-sk" style={{ height: 260 }} /> : (
              <div style={{ height: 260, position: 'relative' }}>
                <ResponsiveContainer>
                  <AreaChart data={chart} margin={{ top: 6, right: 6, left: -22, bottom: 0 }}>
                    <defs>{ROLES.map((r) => (
                      <linearGradient key={r.key} id={'g' + r.key} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={r.color} stopOpacity={0.55} /><stop offset="100%" stopColor={r.color} stopOpacity={0.02} />
                      </linearGradient>))}</defs>
                    <CartesianGrid stroke="rgba(255,255,255,.06)" vertical={false} />
                    <XAxis dataKey="label" tick={{ fill: '#8f99b8', fontSize: 12 }} axisLine={false} tickLine={false} interval="preserveStartEnd" minTickGap={24} />
                    <YAxis allowDecimals={false} tick={{ fill: '#8f99b8', fontSize: 12 }} axisLine={false} tickLine={false} />
                    <Tooltip cursor={{ stroke: 'rgba(255,255,255,.15)' }} contentStyle={{ background: '#151b34', border: '1px solid rgba(255,255,255,.1)', borderRadius: 12, color: '#e9edf9', fontSize: 13 }} />
                    {ROLES.map((r) => <Area key={r.key} type="monotone" dataKey={r.key} name={r.label} stackId="1" stroke={r.color} strokeWidth={2} fill={`url(#g${r.key})`} />)}
                  </AreaChart>
                </ResponsiveContainer>
                {!hasActivity && <div className="adm-empty" style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}><b>No activity yet</b>Sign-ins will appear here.</div>}
              </div>
            )}
          </div>

          <div className="adm-card">
            <div className="adm-h"><h2>Logins by role</h2></div>
            {!m ? <div className="adm-sk" style={{ height: 200 }} /> : ROLES.map((r) => {
              const v = lg[r.key] || { success: 0, failed: 0 }
              const t = v.success + v.failed
              return (
                <div className="adm-role" key={r.key}>
                  <div className="adm-role-h"><span><i style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: r.color, marginRight: 8 }} />{r.label}</span>
                    <span>{v.success} ok · {v.failed} failed</span></div>
                  <div className="adm-bar" style={t ? undefined : { background: 'rgba(255,255,255,.08)' }}><div style={{ width: t ? `${(v.success / t) * 100}%` : 0 }} /></div>
                </div>
              )
            })}
          </div>
        </section>

        <section className="adm-grid2">
          <div className="adm-card">
            <div className="adm-h"><h2>Failed payments</h2></div>
            {!m ? <div className="adm-sk" style={{ height: 120 }} /> : m.failed_payments.length ? (
              <div className="adm-scroll"><table className="adm-table">
                <thead><tr><th>When</th><th>Who</th><th>Plan</th><th>Amount</th><th>Reason</th></tr></thead>
                <tbody>{m.failed_payments.map((p) => (
                  <tr key={p.merchant_order_id}><td>{when(p.created_at)}</td><td style={{ textTransform: 'capitalize' }}>{p.owner_kind}</td><td>{p.plan_type}</td>
                    <td>{inr(p.amount_paise / 100)}</td><td style={{ color: '#fda4af' }}>{p.failure_reason || '-'}</td></tr>))}</tbody>
              </table></div>
            ) : <div className="adm-empty"><b>No failed payments</b>Nothing needs your attention.</div>}
          </div>

          <div className="adm-card">
            <div className="adm-h"><h2>Payments by status</h2></div>
            {!m ? <div className="adm-sk" style={{ height: 120 }} /> : Object.keys(pay).length ? Object.entries(pay).map(([s, v]) => (
              <div className="adm-pay" key={s}>
                <span className="adm-pill" style={{ background: (STATE_COLOR[s] || '#8f99b8') + '22', color: STATE_COLOR[s] || '#8f99b8' }}>{s}</span>
                <span>{v.count} · {inr(v.amount_paise / 100)}</span>
              </div>
            )) : <div className="adm-empty"><b>No payments yet</b>They'll show once billing is live.</div>}
          </div>
        </section>

        <section className="adm-card">
          <div className="adm-h"><h2>AI summary</h2>
            <button className="adm-btn sm" onClick={generate} disabled={busy}>{busy ? <><span className="adm-spin" />Generating</> : <><Icon n="spark" style={{ width: 15, height: 15 }} />Generate for {days}d</>}</button></div>
          {sums.length === 0 ? <div className="adm-empty"><b>No summaries yet</b>Generate one to get a plain-language recap.</div>
            : sums.map((s, i) => (
              <div key={s.id} className={'adm-sum' + (i === 0 ? ' latest' : '')}>
                <small>{i === 0 ? 'Latest · ' : ''}{when(s.created_at)}</small>
                <p>{s.text}</p>
              </div>))}
        </section>
      </main>
    </div>
  )
}

export default function AdminDashboard() {
  const [token, setToken] = useState(() => sessionStorage.getItem(TK))
  const logout = useCallback(() => { sessionStorage.removeItem(TK); setToken(null) }, [])
  return token ? <Dashboard token={token} onLogout={logout} /> : <Login onToken={setToken} />
}
