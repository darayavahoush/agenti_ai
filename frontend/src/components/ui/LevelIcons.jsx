// Level icons for BreathQuest — same visual language as Creatures.jsx
// (soft gradient fill, warm dark linework) but simpler glyphs since these
// sit small in data tables/pickers rather than as full character art.
import { useId } from 'react'

function Pinwheel({ uid }) {
  const g = `pin-${uid}`
  return (
    <svg viewBox="0 0 100 100" className="w-full h-full">
      <defs>
        <linearGradient id={g} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#FFD6E8" /><stop offset="100%" stopColor="#F0679B" />
        </linearGradient>
      </defs>
      <circle cx="50" cy="50" r="6" fill="#B5406F" />
      {[0, 90, 180, 270].map(rot => (
        <path key={rot} d="M50 50 Q50 20 68 22 Q56 34 50 50 Z" fill={`url(#${g})`}
              transform={`rotate(${rot} 50 50)`} />
      ))}
    </svg>
  )
}

function FloatRider({ uid }) {
  const g = `float-${uid}`
  return (
    <svg viewBox="0 0 100 100" className="w-full h-full">
      <defs>
        <linearGradient id={g} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#DCEEFF" /><stop offset="100%" stopColor="#6FB8F0" />
        </linearGradient>
      </defs>
      <ellipse cx="50" cy="46" rx="30" ry="18" fill={`url(#${g})`} />
      <ellipse cx="30" cy="52" rx="16" ry="11" fill={`url(#${g})`} />
      <ellipse cx="70" cy="52" rx="16" ry="11" fill={`url(#${g})`} />
      <path d="M40 66 L44 78 M50 66 L50 80 M60 66 L56 78" stroke="#4A88BF" strokeWidth="3"
            strokeLinecap="round" fill="none" />
    </svg>
  )
}

function Candle({ uid }) {
  const g = `candle-${uid}`
  return (
    <svg viewBox="0 0 100 100" className="w-full h-full">
      <defs>
        <linearGradient id={g} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#FFE8A8" /><stop offset="100%" stopColor="#F0A83B" />
        </linearGradient>
      </defs>
      <rect x="38" y="46" width="24" height="40" rx="4" fill={`url(#${g})`} />
      <ellipse cx="50" cy="46" rx="12" ry="4" fill="#FFF3D0" />
      <path d="M50 36 Q44 26 50 16 Q56 26 50 36 Z" fill="#F0793B" />
      <path d="M50 32 Q47 26 50 20 Q53 26 50 32 Z" fill="#FFD08A" />
    </svg>
  )
}

function Balloon({ uid }) {
  const g = `balloon-${uid}`
  return (
    <svg viewBox="0 0 100 100" className="w-full h-full">
      <defs>
        <linearGradient id={g} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#D6FFE0" /><stop offset="100%" stopColor="#2FB86F" />
        </linearGradient>
      </defs>
      <ellipse cx="50" cy="42" rx="26" ry="30" fill={`url(#${g})`} />
      <path d="M44 70 L50 78 L56 70 Z" fill="#1E8C56" />
      <path d="M50 80 Q56 88 50 96 Q44 88 50 80 Z" stroke="#1E8C56" strokeWidth="2" fill="none" />
      <ellipse cx="40" cy="30" rx="6" ry="9" fill="white" opacity="0.35" />
    </svg>
  )
}

function Dandelion({ uid }) {
  const g = `dand-${uid}`
  return (
    <svg viewBox="0 0 100 100" className="w-full h-full">
      <defs>
        <linearGradient id={g} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#FFFDF0" /><stop offset="100%" stopColor="#E8D9F0" />
        </linearGradient>
      </defs>
      <line x1="50" y1="60" x2="50" y2="90" stroke="#8FBF6F" strokeWidth="3" strokeLinecap="round" />
      <circle cx="50" cy="46" r="16" fill={`url(#${g})`} />
      {[...Array(10)].map((_, i) => {
        const a = (i / 10) * Math.PI * 2
        const x2 = 50 + Math.cos(a) * 24, y2 = 46 + Math.sin(a) * 24
        return <line key={i} x1={50 + Math.cos(a) * 15} y1={46 + Math.sin(a) * 15}
                     x2={x2} y2={y2} stroke="#C9B8DE" strokeWidth="1.5" />
      })}
    </svg>
  )
}

function Dragon({ uid }) {
  const g = `dragon-${uid}`
  return (
    <svg viewBox="0 0 100 100" className="w-full h-full">
      <defs>
        <linearGradient id={g} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#B6F5B0" /><stop offset="100%" stopColor="#2FB86F" />
        </linearGradient>
        <linearGradient id={`${g}-flame`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#FFD08A" /><stop offset="100%" stopColor="#F0793B" />
        </linearGradient>
      </defs>
      <ellipse cx="42" cy="52" rx="24" ry="20" fill={`url(#${g})`} />
      <path d="M36 22 L40 12 L45 25 M48 20 L52 8 L57 23" fill={`url(#${g})`} />
      <path d="M64 50 Q84 46 90 56 Q80 58 72 62 Q80 66 84 74 Q70 72 64 60 Z" fill={`url(#${g}-flame)`} />
    </svg>
  )
}

const ICONS = {
  pinwheel: Pinwheel, float_rider: FloatRider, candle: Candle,
  balloon: Balloon, dandelion: Dandelion, dragon: Dragon,
}

// Drop-in replacement for {LEVEL_EMOJIS[level_id]} — same call site shape,
// just renders SVG instead of an emoji glyph.
export function LevelIcon({ id, className = 'w-7 h-7' }) {
  const uid = useId()
  const Icon = ICONS[id]
  if (!Icon) return null
  return <span className={`inline-block ${className}`}><Icon uid={uid} /></span>
}
