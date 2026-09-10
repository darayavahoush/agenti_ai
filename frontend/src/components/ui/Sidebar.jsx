import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ChevronLeft, ChevronRight, LogOut, Wind, Lock, Users, X, Plus, Check } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

// Role-aware collapsible sidebar for authenticated pages (therapist +
// parent). Background is the SAME vertical gradient as the landing page
// (Landing.jsx's `background:` style) — deliberately not a role-specific
// bg color, so the sidebar reads as "the app's chrome" rather than a
// disconnected panel bolted onto whichever dashboard it's in. Role
// identity still comes through clearly via the accent color (teal for
// therapist, coral for parent) on the logo glow, active nav item, and
// hover states.
const LANDING_GRADIENT = 'linear-gradient(180deg, #12142E 0%, #241F49 38%, #6B4A8A 78%, #9A5F72 100%)'

const THEMES = {
  therapist: {
    glow: 'bg-brand-teal/15 border-brand-teal/25 text-brand-teal',
    accentBar: 'bg-brand-teal',
    activeBg: 'bg-white/10 border-white/10 text-white',
    inactiveText: 'text-white/55 hover:text-white hover:bg-white/[0.06]',
    subtitleText: 'text-white/40',
    nameText: 'text-white',
    divider: 'bg-white/10',
  },
  parent: {
    glow: 'bg-coral/20 border-coral/30 text-coral-light',
    accentBar: 'bg-coral',
    activeBg: 'bg-white/10 border-white/10 text-paper',
    inactiveText: 'text-paper/55 hover:text-paper hover:bg-white/[0.06]',
    subtitleText: 'text-paper/40',
    nameText: 'text-paper',
    divider: 'bg-white/10',
  },
  // Ember/dusk palette matching GameNavbar (the top bar this replaces),
  // so swapping in the sidebar doesn't change kid-facing pages' established
  // visual identity, just the layout shape.
  kid: {
    glow: 'bg-[#FF9B54]/15 border-[#FF9B54]/25 text-[#FF9B54]',
    accentBar: 'bg-[#FF9B54]',
    activeBg: 'bg-white/10 border-white/10 text-white',
    inactiveText: 'text-white/55 hover:text-white hover:bg-white/[0.06]',
    subtitleText: 'text-white/40',
    nameText: 'text-white',
    divider: 'bg-white/10',
  },
}

const ROLE_LABEL = { therapist: 'Therapist', parent: 'Parent', patient: 'Kid' }

function accountDisplayName(a) {
  return a.userData?.first_name || a.userData?.full_name || a.userData?.email || 'Account'
}

function AccountAvatar({ account }) {
  const t = THEMES[account.userType === 'patient' ? 'kid' : account.userType] || THEMES.therapist
  if (account.userData?.avatar) {
    return (
      <span className={`w-9 h-9 rounded-full border flex items-center justify-center shrink-0 text-lg ${t.glow}`}>
        {account.userData.avatar}
      </span>
    )
  }
  const initials = accountDisplayName(account).slice(0, 2).toUpperCase()
  return (
    <span className={`w-9 h-9 rounded-full border flex items-center justify-center shrink-0 text-xs font-semibold ${t.glow}`}>
      {initials}
    </span>
  )
}

// Netflix-style profile picker: everyone who has logged in on this device
// before, switchable instantly with no PIN/password re-entry (per product
// decision -- convenience for a shared family/clinic device outweighs the
// re-auth friction here, since each profile still needed real credentials
// the first time it was added). "Log out" (the separate NavItem below)
// stays the way to actually sign a profile out of the device for good;
// this is for handing the device to someone else who's already used it.
function ProfileSwitcherModal({ onClose }) {
  const { knownAccounts, switchAccount, forgetAccount, currentAccountKey } = useAuth()
  const [busyKey, setBusyKey] = useState(null)
  const [expiredMsg, setExpiredMsg] = useState(null)

  const handleSwitch = async (key) => {
    if (key === currentAccountKey) { onClose(); return }
    setBusyKey(key)
    const result = await switchAccount(key)
    setBusyKey(null)
    if (result.ok) {
      // Full reload rather than a router push -- every page's data (patient
      // list, game state, dashboard queries) was fetched for the PREVIOUS
      // profile; a reload is the simplest way to guarantee nothing from
      // that session lingers in memory under the new one.
      window.location.href = '/'
    } else {
      setExpiredMsg('That session has expired — log in again to use it.')
    }
  }

  const handleForget = async (e, key) => {
    e.stopPropagation()
    await forgetAccount(key)
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-2xl border border-white/10 bg-[#1B1730] shadow-2xl p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-white font-display text-lg font-bold">Switch profile</h2>
          <button onClick={onClose} className="text-white/50 hover:text-white p-1" aria-label="Close">
            <X size={18} />
          </button>
        </div>

        {expiredMsg && (
          <p className="text-xs text-amber-300 bg-amber-400/10 border border-amber-400/20 rounded-lg px-3 py-2 mb-3">
            {expiredMsg}
          </p>
        )}

        <div className="flex flex-col gap-1 max-h-[50vh] overflow-y-auto">
          {knownAccounts.map((a) => {
            const isCurrent = a.key === currentAccountKey
            return (
              <div
                key={a.key}
                onClick={() => handleSwitch(a.key)}
                className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 cursor-pointer transition-colors
                            ${isCurrent ? 'bg-white/10' : 'hover:bg-white/[0.06]'}
                            ${busyKey === a.key ? 'opacity-50 pointer-events-none' : ''}`}
              >
                <AccountAvatar account={a} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-white truncate">{accountDisplayName(a)}</p>
                  <p className="text-xs text-white/40">{ROLE_LABEL[a.userType] || a.userType}</p>
                </div>
                {isCurrent && <Check size={16} className="text-brand-green shrink-0" />}
                <button
                  onClick={(e) => handleForget(e, a.key)}
                  className="opacity-0 group-hover:opacity-100 text-white/30 hover:text-white/70 p-1 shrink-0 transition-opacity"
                  aria-label={`Remove ${accountDisplayName(a)} from this device`}
                  title="Remove from this device"
                >
                  <X size={14} />
                </button>
              </div>
            )
          })}
        </div>

        <Link
          to="/"
          className="mt-3 flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium
                     text-white/70 hover:text-white hover:bg-white/[0.06] transition-colors"
        >
          <Plus size={16} />
          Add another account
        </Link>
      </div>
    </div>
  )
}

function NavItem({ label, Icon, active, collapsed, t, to, onClick, locked, lockedHint }) {
  const [hovered, setHovered] = useState(false)
  const cls = `group relative flex items-center gap-3 pl-3 pr-3 py-2.5 rounded-xl border border-transparent
                transition-all duration-150 ${active ? t.activeBg : t.inactiveText}
                ${!active ? 'hover:translate-x-0.5' : ''}
                ${locked ? 'opacity-40 hover:!translate-x-0 cursor-not-allowed' : ''}`

  const inner = (
    <>
      {/* Active-route accent bar, replacing a flat background tint as the
          primary "you are here" signal — reads faster at a glance and
          survives the busier gradient backdrop better than a subtle bg
          shift alone would. */}
      <span
        className={`absolute left-0 top-1/2 -translate-y-1/2 w-1 rounded-full transition-all duration-150
                    ${active ? `h-5 ${t.accentBar}` : 'h-0'}`}
      />
      <Icon size={18} className="shrink-0" />
      {!collapsed && <span className="text-sm font-medium truncate">{label}</span>}
      {locked && <Lock size={12} className="shrink-0 ml-auto opacity-80" />}
    </>
  )

  return (
    <div
      className="relative"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {locked ? (
        // Not a real Link -- navigating here would just get silently
        // bounced back by ProtectedKid (assessment_completed gate), which
        // is exactly the confusing loop this is meant to prevent. Instead
        // this stays put and explains itself via the tooltip below.
        <button type="button" className={cls + ' w-full text-left'} aria-disabled="true">{inner}</button>
      ) : to ? (
        <Link to={to} className={cls}>{inner}</Link>
      ) : (
        <button onClick={onClick} className={cls + ' w-full text-left'}>{inner}</button>
      )}
      {/* Floating tooltip — shown for locked items on hover regardless of
          collapsed state (that's the whole point: explain why), and for
          any item's label when the sidebar itself is collapsed. */}
      {(locked || collapsed) && hovered && (
        <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 px-2.5 py-1.5 rounded-lg
                         bg-[#12142E] border border-white/10 shadow-lg text-xs font-medium text-white
                         whitespace-nowrap z-50 pointer-events-none max-w-[180px] whitespace-normal">
          {locked ? (lockedHint || 'Locked for now') : label}
        </div>
      )}
    </div>
  )
}

export default function Sidebar({
  role = 'therapist',   // 'therapist' | 'parent'
  items = [],            // [{ label, icon: LucideIcon, to?, onClick?, locked?, lockedHint? }]
  name,
  subtitle,
  onLogout,
}) {
  const [collapsed, setCollapsed] = useState(false)
  const [switcherOpen, setSwitcherOpen] = useState(false)
  const location = useLocation()
  const t = THEMES[role] || THEMES.therapist
  const { knownAccounts } = useAuth() || {}

  return (
    <aside
      style={{ background: LANDING_GRADIENT }}
      className={`sticky top-0 h-dvh shrink-0 flex flex-col border-r border-white/[0.08]
                  shadow-[4px_0_24px_-8px_rgba(0,0,0,0.5)]
                  transition-[width] duration-200 ${collapsed ? 'w-[72px]' : 'w-64'}`}
    >
      <div className="flex items-center gap-3 px-4 py-5">
        <div className={`w-9 h-9 rounded-xl border flex items-center justify-center shrink-0 ${t.glow}`}>
          <Wind size={18} />
        </div>
        {!collapsed && (
          <span className="font-display text-lg font-bold text-white truncate">
            Vaak<span className="text-brand-green">Games</span>
          </span>
        )}
      </div>

      <div className={`h-px mx-4 ${t.divider}`} />

      <nav className="flex-1 px-3 py-4 flex flex-col gap-1 overflow-y-auto overflow-x-visible">
        {items.map(({ label, icon: Icon, to, onClick, locked, lockedHint }) => (
          <NavItem
            key={label}
            label={label}
            Icon={Icon}
            active={!!to && location.pathname === to}
            collapsed={collapsed}
            t={t}
            to={to}
            onClick={onClick}
            locked={locked}
            lockedHint={lockedHint}
          />
        ))}
      </nav>

      <div className={`h-px mx-4 ${t.divider}`} />

      <div className="px-3 py-4 flex flex-col gap-3">
        {!collapsed && (name || subtitle) && (
          <div className="px-3">
            {name && <p className={`text-sm font-medium leading-tight truncate ${t.nameText}`}>{name}</p>}
            {subtitle && <p className={`text-xs leading-tight truncate ${t.subtitleText}`}>{subtitle}</p>}
          </div>
        )}
        {/* Only worth showing once there's more than the current profile to
            switch to -- with just one, "Log out" already covers it and an
            always-visible "Switch profile" that opens to an empty-ish list
            would just be confusing chrome. */}
        {knownAccounts?.length > 1 && (
          <NavItem label="Switch profile" Icon={Users} collapsed={collapsed} t={t} onClick={() => setSwitcherOpen(true)} />
        )}
        <NavItem label="Log out" Icon={LogOut} collapsed={collapsed} t={t} onClick={onLogout} />
        <button
          onClick={() => setCollapsed((c) => !c)}
          className={`flex items-center justify-center gap-2 px-3 py-2 rounded-xl transition-colors ${t.inactiveText}`}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          {!collapsed && <span className="text-xs">Collapse</span>}
        </button>
      </div>
      {switcherOpen && <ProfileSwitcherModal onClose={() => setSwitcherOpen(false)} />}
    </aside>
  )
}
