// Builds a round of VaakMirror sounds that leans on the sounds the Alphabet
// check flagged as tricky (see the agent's `focus_sounds`), while still
// mixing in other sounds so a round isn't the same one or two sounds on
// repeat. With no focus sounds it is exactly the old behaviour: a shuffle
// of the pool, sliced to `size`.
//
//   pool      sounds the game would normally draw from right now
//   size      how many sounds the round needs
//   focusIds  sound ids to over-sample, trickiest first
//   allSounds full taxonomy, used only when a focus sound isn't in `pool`
//             (e.g. a single sound while Mirror, Mirror is on its blends tier)

// Fraction of a round given to focus sounds. Over half, never all of it.
const FOCUS_SHARE = 0.6

const shuffle = (arr) => [...arr].sort(() => Math.random() - 0.5)

export function pickFocusedRound(pool, size, focusIds = [], allSounds = pool) {
  const source = pool.length >= size ? pool : allSounds
  const focus = (focusIds || [])
    .map((id) => allSounds.find((s) => s.id === id))
    .filter(Boolean)
  if (focus.length === 0) return shuffle(source).slice(0, size)

  const focusSlots = Math.min(size, Math.max(1, Math.round(size * FOCUS_SHARE)))
  const picked = []
  // Cycle the focus sounds, trickiest first, so each shows up before any repeats.
  for (let i = 0; i < focusSlots; i++) picked.push(focus[i % focus.length])

  const taken = new Set(picked.map((s) => s.id))
  const rest = shuffle(source.filter((s) => !taken.has(s.id)))
  for (const s of rest) {
    if (picked.length >= size) break
    picked.push(s)
  }
  // Pool too small to fill the round: top up from the full taxonomy.
  for (const s of shuffle(allSounds)) {
    if (picked.length >= size) break
    if (!picked.includes(s)) picked.push(s)
  }

  // Shuffle, then break up back-to-back repeats where there is anything to swap with.
  const out = shuffle(picked).slice(0, size)
  for (let i = 1; i < out.length; i++) {
    if (out[i].id !== out[i - 1].id) continue
    const j = out.findIndex((s, k) => k > i && s.id !== out[i].id && (k + 1 >= out.length || out[k + 1].id !== out[i].id))
    if (j !== -1) [out[i], out[j]] = [out[j], out[i]]
  }
  return out
}
