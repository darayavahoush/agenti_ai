// Extracted from index.jsx into its own file so components that index.jsx
// itself re-exports (e.g. Sidebar.jsx) can import Avatar directly without
// creating a circular import back through the barrel file.
import { Creature, CREATURE_ACCENTS } from './Creatures'

export function Avatar({ avatar = 'chick', photoUrl = null, size = 'md', name = '' }) {
  const sizes = {
    sm:  'w-8 h-8',
    md:  'w-12 h-12',
    lg:  'w-16 h-16',
    xl:  'w-24 h-24',
  }

  // Custom uploaded photo takes priority over the creature species art
  // wherever it's set -- see MyAccount.jsx's upload flow.
  if (photoUrl) {
    const apiBase = (import.meta.env.VITE_API_URL || '').replace(/\/api\/v1$/, '')
    return (
      <div className={`${sizes[size]} rounded-full flex-shrink-0 overflow-hidden`} title={name}>
        <img src={`${apiBase}${photoUrl}`} alt={name} className="w-full h-full object-cover" />
      </div>
    )
  }

  const accent = CREATURE_ACCENTS[avatar] || CREATURE_ACCENTS.chick
  return (
    <div
      className={`${sizes[size]} rounded-full flex items-center justify-center flex-shrink-0 p-1`}
      style={{ background: `linear-gradient(160deg, ${accent.from}33, ${accent.to}22)` }}
      title={name}
    >
      <Creature species={avatar} className="w-full h-full" />
    </div>
  )
}
