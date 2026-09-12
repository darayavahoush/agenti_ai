// Shared UI primitives

export function Button({ children, variant = 'primary', size = 'md', className = '', ...props }) {
  const base = 'inline-flex items-center justify-center gap-2 font-semibold rounded-xl transition-all duration-200 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed'
  const variants = {
    primary: 'bg-brand-green text-brand-dark hover:bg-opacity-90',
    ghost:   'border border-white/20 text-white hover:bg-white/10',
    danger:  'bg-brand-coral text-white hover:bg-opacity-90',
    teal:    'bg-brand-teal text-white hover:bg-opacity-90',
  }
  const sizes = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-sm',
    lg: 'px-8 py-4 text-base',
  }
  return (
    <button className={`${base} ${variants[variant]} ${sizes[size]} ${className}`} {...props}>
      {children}
    </button>
  )
}

export function Card({ children, className = '', as: Tag = 'div', ...props }) {
  return (
    <Tag
      className={`bg-gradient-to-b from-white/[0.045] to-white/[0.015] border border-white/[0.08]
        rounded-2xl p-6 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06),0_4px_20px_-6px_rgba(0,0,0,0.4)]
        ${className}`}
      {...props}
    >
      {children}
    </Tag>
  )
}

export function Input({ label, error, icon: Icon, rightElement, className = '', ...props }) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && <label className="text-sm font-medium text-white/70">{label}</label>}
      <div className="relative">
        {Icon && (
          <Icon className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30 pointer-events-none" />
        )}
        <input
          className={`w-full bg-white/5 border ${error ? 'border-brand-coral' : 'border-white/15'}
            rounded-xl px-4 py-3 ${Icon ? 'pl-10' : ''} ${rightElement ? 'pr-10' : ''} text-white placeholder-white/30
            focus:outline-none focus:border-brand-green transition-colors ${className}`}
          {...props}
        />
        {rightElement && (
          <div className="absolute right-3.5 top-1/2 -translate-y-1/2">
            {rightElement}
          </div>
        )}
      </div>
      {error && <span className="text-xs text-brand-coral">{error}</span>}
    </div>
  )
}

export function Badge({ children, color = 'green' }) {
  const colors = {
    green:  'bg-brand-green/15 text-brand-green border-brand-green/25',
    amber:  'bg-brand-amber/15 text-brand-amber border-brand-amber/25',
    coral:  'bg-brand-coral/15 text-brand-coral border-brand-coral/25',
    purple: 'bg-brand-purple/15 text-purple-300 border-brand-purple/25',
    gray:   'bg-white/[0.06] text-white/60 border-white/10',
  }
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${colors[color]}`}>
      {children}
    </span>
  )
}

export function Spinner({ size = 'md' }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' }
  return (
    <div className={`${sizes[size]} border-2 border-white/20 border-t-brand-green rounded-full animate-spin`} />
  )
}

// Meteor sparkle mark -- a breathing sparkle core with soft pulse halos
// and a handful of meteors streaking past at staggered angles/speeds/
// delays, echoing the twinkling starfield used elsewhere in the app
// (PlayfulBackdrop) rather than a generic spinner or EQ-style bars.
export function SparkLoader({ size = 'lg' }) {
  const px = { sm: 28, md: 46, lg: 72 }[size] || 72
  const scale = px / 90
  return (
    <div style={{ width: px, height: px, position: 'relative' }}>
      <div
        className="spark-loader-inner"
        style={{
          position: 'absolute', top: '50%', left: '50%', width: 90, height: 90,
          transform: `translate(-50%, -50%) scale(${scale})`, transformOrigin: 'center',
        }}
      >
        <div className="sl-meteor sl-m1" style={{ position: 'absolute', top: 8, left: -6, width: 16, height: 2, background: 'linear-gradient(to right, transparent, #A78BFA)', transform: 'rotate(28deg)' }} />
        <div className="sl-meteor sl-m2" style={{ position: 'absolute', top: 38, left: 82, width: 14, height: 2, background: 'linear-gradient(to left, transparent, #5FD0F3)', transform: 'rotate(200deg)' }} />
        <div className="sl-meteor sl-m3" style={{ position: 'absolute', top: 76, left: 6, width: 12, height: 2, background: 'linear-gradient(to right, transparent, #FF8FE0)', transform: 'rotate(-18deg)' }} />
        <div className="sl-meteor sl-m4" style={{ position: 'absolute', top: 0, left: 60, width: 13, height: 2, background: 'linear-gradient(to right, transparent, #A78BFA)', transform: 'rotate(60deg)' }} />
        <div style={{ position: 'absolute', top: '50%', left: '50%', width: 56, height: 56, marginTop: -28, marginLeft: -28, borderRadius: '50%', background: 'rgba(167,139,250,0.10)', animation: 'sl-ringpulse 2.2s ease-in-out infinite' }} />
        <div style={{ position: 'absolute', top: '50%', left: '50%', width: 34, height: 34, marginTop: -17, marginLeft: -17, borderRadius: '50%', background: 'rgba(167,139,250,0.18)', animation: 'sl-ringpulse 2.2s ease-in-out 0.15s infinite' }} />
        <div
          className="sl-spark"
          style={{
            position: 'absolute', top: '50%', left: '50%', width: 26, height: 26, marginTop: -13, marginLeft: -13,
            background: '#A78BFA', clipPath: 'polygon(50% 0%, 61% 39%, 100% 50%, 61% 61%, 50% 100%, 39% 61%, 0% 50%, 39% 39%)',
          }}
        />
      </div>
      <style>{`
        @keyframes sl-ringpulse { 0%, 100% { transform: scale(0.9); opacity: 0.5; } 50% { transform: scale(1.12); opacity: 1; } }
        .sl-spark { animation: sl-sparkle 2.2s ease-in-out infinite; }
        @keyframes sl-sparkle { 0%, 100% { transform: scale(0.85) rotate(0deg); opacity: 0.85; } 50% { transform: scale(1.15) rotate(25deg); opacity: 1; } }
        .sl-meteor { opacity: 0; border-radius: 2px; }
        .sl-m1 { animation: sl-fly1 2.6s ease-in 0.2s infinite; }
        .sl-m2 { animation: sl-fly2 3.1s ease-in 1.1s infinite; }
        .sl-m3 { animation: sl-fly3 2.3s ease-in 1.9s infinite; }
        .sl-m4 { animation: sl-fly4 3.4s ease-in 0.7s infinite; }
        @keyframes sl-fly1 { 0% { opacity: 0; transform: rotate(28deg) translateX(0); } 8% { opacity: 1; } 25% { opacity: 0; transform: rotate(28deg) translateX(75px); } 100% { opacity: 0; transform: rotate(28deg) translateX(75px); } }
        @keyframes sl-fly2 { 0% { opacity: 0; transform: rotate(200deg) translateX(0); } 8% { opacity: 1; } 22% { opacity: 0; transform: rotate(200deg) translateX(70px); } 100% { opacity: 0; transform: rotate(200deg) translateX(70px); } }
        @keyframes sl-fly3 { 0% { opacity: 0; transform: rotate(-18deg) translateX(0); } 8% { opacity: 1; } 28% { opacity: 0; transform: rotate(-18deg) translateX(65px); } 100% { opacity: 0; transform: rotate(-18deg) translateX(65px); } }
        @keyframes sl-fly4 { 0% { opacity: 0; transform: rotate(60deg) translateX(0); } 8% { opacity: 1; } 24% { opacity: 0; transform: rotate(60deg) translateX(60px); } 100% { opacity: 0; transform: rotate(60deg) translateX(60px); } }
        @media (prefers-reduced-motion: reduce) {
          .sl-meteor { display: none; }
          .sl-spark, [style*="sl-ringpulse"] { animation: none; }
        }
      `}</style>
    </div>
  )
}

export function StarRating({ stars = 0, max = 3, size = 'md' }) {
  const sizes = { sm: 'text-lg', md: 'text-2xl', lg: 'text-3xl' }
  return (
    <span className={sizes[size]}>
      {Array.from({ length: max }, (_, i) => (
        <span key={i} className={i < stars ? 'text-brand-amber' : 'text-white/20'}>★</span>
      ))}
    </span>
  )
}

export { Avatar } from './Avatar'

export function PageLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <SparkLoader size="lg" />
        <p className="text-white/50 text-sm">Just a moment…</p>
      </div>
    </div>
  )
}

// Real lucide icon in a colored badge + a big, tight-tracked number —
// replaces the bare Card+emoji+number pattern dashboards otherwise
// reach for independently.
export function StatCard({ icon: Icon, value, label, accent = '#2FB8A6' }) {
  return (
    <Card className="flex flex-col gap-3">
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center"
        style={{ backgroundColor: `${accent}1f`, border: `1px solid ${accent}33` }}
      >
        <Icon size={18} style={{ color: accent }} />
      </div>
      <div>
        <p className="font-display text-2xl font-bold text-white tracking-tight leading-none">{value}</p>
        <p className="text-white/40 text-xs mt-1.5">{label}</p>
      </div>
    </Card>
  )
}
export { default as Sidebar, ProfileSwitcherModal } from './Sidebar'
export { default as AmbientGlow } from './AmbientGlow'
export { default as SupervisedBanner } from './SupervisedBanner'
export { default as OfflineBanner } from './OfflineBanner'
export { default as ChildSwitcher } from './ChildSwitcher'
export { default as SavedProfilesGate } from './SavedProfilesGate'
