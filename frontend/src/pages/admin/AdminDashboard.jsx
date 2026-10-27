import { useCallback, useEffect, useMemo, useState } from 'react'
import { AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import './admin.css'

const BASE = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '')
const API = BASE + '/admin'
const TK = 'admin_token'
const C = { kid: 'var(--kid)', parent: 'var(--ok)', therapist: 'var(--warn)', ok: 'var(--ok)', bad: 'var(--bad)', warn: 'var(--warn)', blue: 'var(--blue)', muted: 'var(--muted)', grid: 'var(--border)' }
const ROLES = [
  { key: 'kid', acc: 'kids', label: 'Kids', color: C.kid },
  { key: 'parent', acc: 'parents', label: 'Parents', color: C.parent },
  { key: 'therapist', acc: 'therapists', label: 'Therapists', color: C.therapist },
]
const ROLE = Object.fromEntries(ROLES.map((r) => [r.key, r]))
const STATE = { completed: C.ok, failed: C.bad, pending: C.warn, created: C.muted, active: C.ok, trialing: C.blue, past_due: C.warn, canceled: C.bad }
const TT = { contentStyle: { background: 'var(--panel2)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text)', fontSize: 13 }, itemStyle: { color: 'var(--text)' }, labelStyle: { color: 'var(--muted)' }, cursor: { fill: 'rgba(128,128,128,.12)', stroke: 'rgba(128,128,128,.3)' } }

const THEME_KEY = 'admin_theme'
function useTheme() {
  const [theme, setTheme] = useState(() => {
    try { const s = localStorage.getItem(THEME_KEY); if (s === 'light' || s === 'dark') return s } catch {}
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
  })
  const toggle = useCallback(() => setTheme((t) => {
    const n = t === 'dark' ? 'light' : 'dark'
    try { localStorage.setItem(THEME_KEY, n) } catch {}
    return n
  }), [])
  return [theme, toggle]
}
const AX = { tick: { fill: C.muted, fontSize: 12 }, axisLine: false, tickLine: false }
const MG = { top: 6, right: 6, left: -24, bottom: 0 }

async function call(path, token, opts = {}) {
  const res = await fetch(API + path, {
    ...opts,
    headers: { 'content-type': 'application/json', ...(token ? { authorization: `Bearer ${token}` } : {}) },
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw Object.assign(new Error(body.detail || 'Request failed'), { status: res.status })
  return body
}

const when = (iso) => new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
const inr = (v) => '₹' + Number(v).toLocaleString('en-IN', { maximumFractionDigits: 2, minimumFractionDigits: 2 })
const num = (v) => Number(v || 0).toLocaleString('en-IN')
const istDay = (back) => new Date(Date.now() + 19800000 - back * 864e5).toISOString().slice(0, 10)
const nice = (s) => s.replace(/([a-z])([A-Z])/g, '$1 $2')

const Dot = ({ c }) => <span className="adm-dot" style={{ background: c }} />
const Status = ({ c, children }) => <span style={{ whiteSpace: 'nowrap' }}><Dot c={c} />{children}</span>
const Card = ({ title, right, children }) => (
  <div className="adm-card"><div className="adm-h"><h2>{title}</h2>{right}</div>{children}</div>
)
const Empty = ({ t, s }) => <div className="adm-empty"><b>{t}</b>{s}</div>
const Sk = ({ h = 220 }) => <div className="adm-sk" style={{ height: h }} />
const Legend = ({ items }) => <div className="adm-legend">{items.map((r) => <span key={r.label}><Dot c={r.color} />{r.label}</span>)}</div>
const Kpi = ({ label, value, sub, color }) => (
  <div className="adm-kpi"><div className="adm-kl">{label}</div><div className="adm-kv" style={{ color }}>{value}</div><div className="adm-ks">{sub}</div></div>
)

function HBars({ items, color = C.blue }) {
  const max = Math.max(1, ...items.map((i) => i.value))
  return items.map((i) => (
    <div className="adm-hb" key={i.label}>
      <div className="adm-hb-h"><span>{i.label}</span><span>{i.right ?? num(i.value)}</span></div>
      <div className="adm-bar"><div style={{ width: `${(i.value / max) * 100}%`, background: i.color || color }} /></div>
    </div>
  ))
}

function Login({ onToken, theme, onTheme }) {
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
    <div className="adm" data-theme={theme}><button className="adm-ghost adm-corner" onClick={onTheme}>{theme === 'dark' ? 'Light' : 'Dark'}</button><div className="adm-center">
      <form className="adm-login" onSubmit={submit}>
        <h1>Sign in</h1>
        <p className="adm-sub">Vaaksudhi admin</p>
        {err && <div className="adm-err" style={{ marginBottom: 14 }}>{err}</div>}
        <label className="adm-field"><span>Email</span>
          <div className="adm-input"><input type="email" autoComplete="username" autoFocus value={email} onChange={(e) => setEmail(e.target.value)} required /></div>
        </label>
        <label className="adm-field"><span>Password</span>
          <div className="adm-input">
            <input type={show ? 'text' : 'password'} autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required style={{ paddingRight: 56 }} />
            <button type="button" className="adm-eye" onClick={() => setShow(!show)}>{show ? 'Hide' : 'Show'}</button>
          </div>
        </label>
        <button className="adm-btn" style={{ width: '100%', marginTop: 6 }} disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
      </form>
    </div></div>
  )
}

function Dashboard({ token, onLogout, theme, onTheme }) {
  const [days, setDays] = useState(7)
  const [m, setM] = useState(null)
  const [o, setO] = useState(null)
  const [sums, setSums] = useState([])
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [tick, setTick] = useState(0)

  const guard = useCallback((ex) => { if (ex.status === 401) onLogout(); else setErr(ex.message) }, [onLogout])

  useEffect(() => {
    setErr(''); setM(null); setO(null)
    call(`/metrics?days=${days}`, token).then(setM).catch(guard)
    call(`/overview?days=${days}`, token).then(setO).catch(guard)
  }, [days, token, guard, tick])
  useEffect(() => { call('/summaries', token).then(setSums).catch(guard) }, [token, guard])

  const generate = async () => {
    setBusy(true); setErr('')
    try { await call(`/summary?days=${days}`, token, { method: 'POST' }); setSums(await call('/summaries', token)) }
    catch (ex) { guard(ex) } finally { setBusy(false) }
  }

  const dayList = useMemo(() => Array.from({ length: days }, (_, i) => istDay(days - 1 - i)), [days])
  const lab = (d) => d.slice(5)

  const dau = useMemo(() => {
    const rows = Object.fromEntries(dayList.map((d) => [d, { label: lab(d), kid: 0, parent: 0, therapist: 0 }]))
    ;(m?.daily_active_users || []).forEach((r) => { if (rows[r.date]) rows[r.date][r.user_type] = r.active_users })
    return Object.values(rows)
  }, [m, dayList])
  const attempts = useMemo(() => {
    const by = Object.fromEntries((o?.auth.by_day || []).map((r) => [r.date, r]))
    return dayList.map((d) => ({ label: lab(d), success: by[d]?.success || 0, failed: by[d]?.failed || 0 }))
  }, [o, dayList])
  const signups = useMemo(() => {
    const by = Object.fromEntries((o?.accounts.daily || []).map((r) => [r.date, r]))
    return dayList.map((d) => ({ label: lab(d), kids: by[d]?.kids || 0, parents: by[d]?.parents || 0, therapists: by[d]?.therapists || 0 }))
  }, [o, dayList])
  const sess = useMemo(() => {
    const by = Object.fromEntries((o?.sessions.daily || []).map((r) => [r.date, r.count]))
    return dayList.map((d) => ({ label: lab(d), count: by[d] || 0 }))
  }, [o, dayList])

  const lg = m?.logins || {}
  const ok = Object.values(lg).reduce((a, v) => a + (v.success || 0), 0)
  const bad = Object.values(lg).reduce((a, v) => a + (v.failed || 0), 0)
  const rate = ok + bad ? Math.round((ok / (ok + bad)) * 100) : null
  const pay = m?.payments_by_state || {}
  const tot = o?.accounts.totals || {}
  const totalAcc = ROLES.reduce((a, r) => a + (tot[r.acc]?.total || 0), 0)
  const newAcc = ROLES.reduce((a, r) => a + (tot[r.acc]?.new || 0), 0)
  const subs = o?.subscriptions || []
  const activeSubs = subs.filter((s) => s.status === 'active').reduce((a, s) => a + s.count, 0)
  const hours = (o?.auth.by_hour || []).map((n, h) => ({ h: String(h).padStart(2, '0'), n }))
  const peak = hours.reduce((a, b) => (b.n > (a?.n ?? -1) ? b : a), null)
  const devTotal = (o?.auth.devices || []).reduce((a, d) => a + d.count, 0)
  const donut = ROLES.map((r) => ({ name: r.label, value: tot[r.acc]?.total || 0, color: r.color }))
  const hasDau = dau.some((r) => r.kid + r.parent + r.therapist > 0)
  const loading = !m || !o

  return (
    <div className="adm" data-theme={theme}>
      <header className="adm-top"><div className="adm-wrap">
        <div className="adm-brand"><b>Vaaksudhi</b><span>Admin</span></div>
        <div className="adm-tools">
          <button className="adm-ghost" onClick={onTheme}>{theme === 'dark' ? 'Light' : 'Dark'}</button>
          <button className="adm-ghost" onClick={() => setTick((t) => t + 1)}>Refresh</button>
          <button className="adm-ghost" onClick={onLogout}>Sign out</button>
        </div>
      </div></header>

      <div className="adm-wrap adm-main">
        <div className="adm-title">
          <div><h1>Overview</h1><p>Usage, accounts and revenue · last {days} days</p></div>
          <div className="adm-seg">{[7, 30, 90].map((d) => <button key={d} className={d === days ? 'on' : ''} onClick={() => setDays(d)}>{d} days</button>)}</div>
        </div>

        {err && <div className="adm-err">{err}</div>}

        {loading ? <Sk h={92} /> : (
          <section className="adm-kpis">
            <Kpi label="Registered accounts" value={num(totalAcc)} sub="all roles" />
            <Kpi label="New signups" value={num(newAcc)} sub={`last ${days} days`} />
            <Kpi label="Successful logins" value={num(ok)} sub={`${num(o.auth.unique_ips)} unique IPs`} />
            <Kpi label="Login success rate" value={rate === null ? '–' : rate + '%'} sub={`${num(bad)} failed`} color={rate !== null && rate < 70 ? C.bad : undefined} />
            <Kpi label="Revenue" value={inr(m.revenue_inr)} sub={`${pay.completed?.count || 0} payments`} />
            <Kpi label="Active subscriptions" value={num(activeSubs)} sub={`${pay.failed?.count || 0} failed payments`} />
          </section>
        )}

        <h3 className="adm-sec">Audience</h3>
        <section className="adm-g a">
          <Card title="Daily active users" right={<Legend items={ROLES} />}>
            {loading ? <Sk /> : (
              <div style={{ height: 250, position: 'relative' }}>
                <ResponsiveContainer>
                  <AreaChart data={dau} margin={MG}>
                    <CartesianGrid stroke={C.grid} vertical={false} />
                    <XAxis dataKey="label" {...AX} interval="preserveStartEnd" minTickGap={24} />
                    <YAxis allowDecimals={false} {...AX} />
                    <Tooltip {...TT} />
                    {ROLES.map((r) => <Area key={r.key} type="monotone" dataKey={r.key} name={r.label} stackId="1" stroke={r.color} strokeWidth={1.5} fill={r.color} fillOpacity={0.18} />)}
                  </AreaChart>
                </ResponsiveContainer>
                {!hasDau && <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', pointerEvents: 'none' }}><Empty t="No successful logins yet" s="Sign in as a kid, parent or therapist and it shows here." /></div>}
              </div>
            )}
          </Card>
          <Card title="Logins by role">
            {loading ? <Sk /> : ROLES.map((r) => {
              const v = lg[r.key] || { success: 0, failed: 0 }
              const t = v.success + v.failed
              return (
                <div className="adm-hb" key={r.key}>
                  <div className="adm-hb-h"><span><Dot c={r.color} />{r.label}</span><span>{v.success} ok · {v.failed} failed</span></div>
                  <div className="adm-bar">{t > 0 && <><div style={{ width: `${(v.success / t) * 100}%`, background: C.ok }} /><div style={{ width: `${(v.failed / t) * 100}%`, background: C.bad }} /></>}</div>
                </div>
              )
            })}
          </Card>
        </section>

        <section className="adm-g b">
          <Card title="Accounts">
            {loading ? <Sk /> : (
              <>
                <div className="adm-donut">
                  <div style={{ height: 160, position: 'relative' }}>
                    {totalAcc > 0 ? (
                      <ResponsiveContainer><PieChart>
                        <Pie data={donut} dataKey="value" innerRadius={50} outerRadius={72} paddingAngle={2} stroke="none">{donut.map((d) => <Cell key={d.name} fill={d.color} />)}</Pie>
                        <Tooltip {...TT} />
                      </PieChart></ResponsiveContainer>
                    ) : <Empty t="No accounts" s="" />}
                    {totalAcc > 0 && <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', pointerEvents: 'none', textAlign: 'center' }}><div><b style={{ fontSize: 22 }}>{num(totalAcc)}</b><div className="adm-note">total</div></div></div>}
                  </div>
                  <div>{ROLES.map((r) => (
                    <div className="adm-row" key={r.key}>
                      <span><Dot c={r.color} />{r.label}</span>
                      <span>{num(tot[r.acc]?.total)}{tot[r.acc]?.new ? <span className="m" style={{ color: C.ok }}> +{tot[r.acc].new}</span> : null}</span>
                    </div>))}</div>
                </div>
                <div className="adm-mini">{ROLES.map((r) => <div key={r.key}><b>{tot[r.acc]?.active ?? '–'}</b><small>{r.label} signed in</small></div>)}</div>
                <p className="adm-note" style={{ marginTop: 10 }}>Signed in = last login falls inside the selected window.</p>
              </>
            )}
          </Card>
          <Card title="New signups per day" right={<Legend items={ROLES} />}>
            {loading ? <Sk /> : (
              <div style={{ height: 250 }}><ResponsiveContainer>
                <BarChart data={signups} margin={MG}>
                  <CartesianGrid stroke={C.grid} vertical={false} />
                  <XAxis dataKey="label" {...AX} interval="preserveStartEnd" minTickGap={24} /><YAxis allowDecimals={false} {...AX} /><Tooltip {...TT} />
                  <Bar dataKey="kids" name="Kids" stackId="a" fill={C.kid} /><Bar dataKey="parents" name="Parents" stackId="a" fill={C.parent} /><Bar dataKey="therapists" name="Therapists" stackId="a" fill={C.therapist} radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer></div>
            )}
          </Card>
        </section>

        <h3 className="adm-sec">Engagement</h3>
        <section className="adm-g b">
          <Card title="Login attempts per day" right={<Legend items={[{ label: 'Success', color: C.ok }, { label: 'Failed', color: C.bad }]} />}>
            {loading ? <Sk /> : (
              <div style={{ height: 250 }}><ResponsiveContainer>
                <BarChart data={attempts} margin={MG}>
                  <CartesianGrid stroke={C.grid} vertical={false} />
                  <XAxis dataKey="label" {...AX} interval="preserveStartEnd" minTickGap={24} /><YAxis allowDecimals={false} {...AX} /><Tooltip {...TT} />
                  <Bar dataKey="success" name="Success" stackId="a" fill={C.ok} /><Bar dataKey="failed" name="Failed" stackId="a" fill={C.bad} radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer></div>
            )}
          </Card>
          <Card title="Busiest hours (IST)" right={peak && peak.n > 0 ? <span className="m">Peak {peak.h}:00</span> : null}>
            {loading ? <Sk /> : (
              <div style={{ height: 250 }}><ResponsiveContainer>
                <BarChart data={hours} margin={MG}>
                  <CartesianGrid stroke={C.grid} vertical={false} />
                  <XAxis dataKey="h" {...AX} interval={2} /><YAxis allowDecimals={false} {...AX} /><Tooltip {...TT} labelFormatter={(h) => `${h}:00`} />
                  <Bar dataKey="n" name="Attempts" fill={C.blue} radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer></div>
            )}
          </Card>
        </section>

        <section className="adm-g b">
          <Card title="Practice sessions per day" right={o?.sessions.best ? <span className="m">{nice(o.sessions.best)}</span> : null}>
            {loading ? <Sk h={230} /> : o.sessions.best ? (
              <div style={{ height: 230 }}><ResponsiveContainer>
                <AreaChart data={sess} margin={MG}>
                  <CartesianGrid stroke={C.grid} vertical={false} />
                  <XAxis dataKey="label" {...AX} interval="preserveStartEnd" minTickGap={24} /><YAxis allowDecimals={false} {...AX} /><Tooltip {...TT} />
                  <Area type="monotone" dataKey="count" name="Sessions" stroke={C.blue} strokeWidth={1.5} fill={C.blue} fillOpacity={0.18} />
                </AreaChart>
              </ResponsiveContainer></div>
            ) : <Empty t="No sessions in this window" s="Game and exercise sessions chart here." />}
          </Card>
          <Card title="Activity by feature">
            {loading ? <Sk h={230} /> : o.sessions.tables.length ? (
              <HBars items={o.sessions.tables.map((t) => ({ label: nice(t.name), value: t.in_window ?? t.total, right: `${num(t.in_window ?? 0)} in window · ${num(t.total)} total` }))} />
            ) : <Empty t="No session tables found" s="" />}
          </Card>
        </section>

        <h3 className="adm-sec">Security and devices</h3>
        <section className="adm-g b">
          <Card title="Devices (successful logins)">
            {loading ? <Sk h={150} /> : devTotal ? (
              <HBars items={o.auth.devices.map((d) => ({ label: d.name, value: d.count, right: `${d.count} · ${Math.round((d.count / devTotal) * 100)}%` }))} />
            ) : <Empty t="No device data yet" s="" />}
          </Card>
          <Card title="Top failing IPs">
            {loading ? <Sk h={150} /> : o.auth.top_failing_ips.length ? (
              <HBars items={o.auth.top_failing_ips.map((i) => ({ label: i.ip, value: i.failed, right: i.failed >= 5 ? `${i.failed} failed · suspicious` : `${i.failed} failed`, color: i.failed >= 5 ? C.bad : C.warn }))} />
            ) : <Empty t="No failed attempts" s="" />}
          </Card>
        </section>

        <h3 className="adm-sec">Revenue</h3>
        <section className="adm-g b">
          <Card title="Subscriptions">
            {loading ? <Sk h={110} /> : subs.length ? subs.map((s) => (
              <div className="adm-row" key={s.status}><Status c={STATE[s.status] || C.muted}>{s.status}</Status><span>{num(s.count)}</span></div>
            )) : <Empty t="No subscriptions" s="" />}
          </Card>
          <Card title="Payments by status">
            {loading ? <Sk h={110} /> : Object.keys(pay).length ? Object.entries(pay).map(([s, v]) => (
              <div className="adm-row" key={s}><Status c={STATE[s] || C.muted}>{s}</Status><span>{v.count} · {inr(v.amount_paise / 100)}</span></div>
            )) : <Empty t="No payments yet" s="They'll show once billing is live." />}
          </Card>
        </section>
        <Card title="Failed payments">
          {loading ? <Sk h={90} /> : m.failed_payments.length ? (
            <div className="adm-scroll"><table className="adm-table">
              <thead><tr><th>When</th><th>Who</th><th>Plan</th><th>Amount</th><th>Mode</th><th>Reason</th></tr></thead>
              <tbody>{m.failed_payments.map((p) => (
                <tr key={p.merchant_order_id}><td>{when(p.created_at)}</td><td style={{ textTransform: 'capitalize' }}>{p.owner_kind}</td><td>{p.plan_type}</td>
                  <td>{inr(p.amount_paise / 100)}</td><td>{p.payment_mode || '–'}</td><td style={{ color: C.bad }}>{p.failure_reason || '–'}</td></tr>))}</tbody>
            </table></div>
          ) : <Empty t="No failed payments" s="Nothing needs attention." />}
        </Card>

        <h3 className="adm-sec">Activity</h3>
        <Card title="Recent sign-ins">
          {loading ? <Sk h={160} /> : o.auth.recent.length ? (
            <div className="adm-scroll"><table className="adm-table">
              <thead><tr><th>When</th><th>Role</th><th>Result</th><th>Device</th><th>IP</th></tr></thead>
              <tbody>{o.auth.recent.map((r) => (
                <tr key={r.id}><td>{when(r.created_at)}</td>
                  <td style={{ textTransform: 'capitalize' }}><Status c={ROLE[r.user_type]?.color || C.muted}>{r.user_type}</Status></td>
                  <td><Status c={r.success ? C.ok : C.bad}>{r.success ? 'Success' : 'Failed'}</Status></td>
                  <td>{r.device}</td><td style={{ color: C.muted }}>{r.ip || '–'}</td></tr>))}</tbody>
            </table></div>
          ) : <Empty t="No activity yet" s="" />}
        </Card>

        <h3 className="adm-sec">Summary</h3>
        <Card title="AI summary" right={<button className="adm-btn sm" onClick={generate} disabled={busy}>{busy ? 'Generating…' : `Generate for ${days} days`}</button>}>
          {sums.length === 0 ? <Empty t="No summaries yet" s="Generate one for a plain-language recap." />
            : sums.map((s, i) => (
              <div key={s.id} className="adm-sum">
                <small>{i === 0 ? 'Latest · ' : ''}{when(s.created_at)}</small>
                <p>{s.text}</p>
              </div>))}
        </Card>
      </div>
    </div>
  )
}

export default function AdminDashboard() {
  const [token, setToken] = useState(() => sessionStorage.getItem(TK))
  const logout = useCallback(() => { sessionStorage.removeItem(TK); setToken(null) }, [])
  const [theme, toggleTheme] = useTheme()
  return token ? <Dashboard token={token} onLogout={logout} theme={theme} onTheme={toggleTheme} /> : <Login onToken={setToken} theme={theme} onTheme={toggleTheme} />
}
