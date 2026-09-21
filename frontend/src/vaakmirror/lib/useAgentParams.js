import { useEffect, useState } from 'react'
import { getAgentParams } from './api.js'

// What the Alphabet check's VaakMirror planner decided for this child:
//   { has_plan, primary_game, focus_sounds, round_size, start_complexity, summary }
// `params` stays null until it loads and on any failure, so a game that
// needs it must treat null as "no plan" and behave exactly as it always did.
export function useAgentParams() {
  const [params, setParams] = useState(null)
  useEffect(() => {
    let cancelled = false
    getAgentParams()
      .then((p) => { if (!cancelled) setParams(p) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])
  return { params }
}
