// lib/agentMessage.js — the difficulty agent's raw decision.message (from
// getAgentDecision/DIFFICULTY_AGENT, both frontend fallback and the trained
// backend policy in backend/agent/service.py) is written for an in-flight
// "here's how you're doing" moment, not for sitting directly under a
// "Sheet complete! You popped every bubble!" success banner. Its "lower"
// wording in particular ("Let's ease up a bit so this feels achievable.")
// reads as an apology or a comment on THIS attempt having gone poorly --
// but the agent is deciding sheet SIZE for the *next* round, often from
// this kid's broader attempt history rather than just the round they just
// aced, so a raw "lower" message can land directly under a win they're
// still celebrating and read as a contradiction.
//
// This reframes the same underlying decision (still fully respected --
// the actual difficulty step still happens in DIFFICULTY_AGENT.apply)
// into copy that's always congratulatory and always about what's coming
// next, never a judgment on the round that just finished successfully.
export function successScreenAgentMessage(decision) {
  if (!decision) return ''
  if (decision.action === 'raise') return "Awesome! Next sheet's a little bigger 🫧"
  if (decision.action === 'lower') return "Nailed it! We'll keep the next one a comfy size 💛"
  return "Nailed it! Same size again next round 🌟"
}
