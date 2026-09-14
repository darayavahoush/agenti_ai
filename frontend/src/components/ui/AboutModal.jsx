import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { Info, X } from 'lucide-react'

// Self-contained "About / How to use" trigger + modal, same pattern as
// ChildSwitcher: owns its own open state, drops into Sidebar's extraFooter
// slot. Content is role-specific (kid/parent/therapist) since each sees a
// very different product surface. Rendered via createPortal(document.body)
// deliberately -- Sidebar's <aside> is `position: sticky`, which creates
// its own stacking context, so any fixed-position modal rendered as a
// normal descendant of it can be silently painted-over by page content in
// a sibling stacking context (see ChildSwitcher/ProfileSwitcherModal fix).
// A future modal added to extraFooter without a portal will hit the exact
// same bug -- if you're adding one, portal it.
//
// Auto-opens once per role on first load (bq_seen_about_<role> flag),
// then only reachable via the sidebar link after that.

const CONTENT = {
  kid: {
    title: 'Welcome, sound explorer! 🚀',
    accent: 'text-[#FF9B54]',
    body: [
      "Did you know your breath is actually magic fuel? Every time you play Pinwheel Spin, you're training your lungs like a superhero trains their powers -- stronger breath means stronger, clearer words.",
      "And here's the wildest part: this app is basically watching you play and thinking, in real time, just like a coach would. Get something tricky? It quietly makes the next round a little gentler. Crushing it? It turns up the fun. It's adjusting itself around YOU, every single time -- nobody else in the world gets that exact game.",
      "Every sound you practice, every level you beat -- it all lights up on a screen your grown-up and your speech therapist can see. You're not just playing a game. You're building a trail of awesome for them to follow and cheer about.",
    ],
  },
  parent: {
    title: 'The story behind this app',
    accent: 'text-coral-light',
    body: [
      "Here's the idea we started with: kids don't practice things because they're told to -- they practice things because they're fun. So instead of speech drills, we built games your child actually wants to come back to, and hid the practice inside the play.",
      "But the more interesting part is what's happening underneath. Every round your child plays feeds a system that's genuinely learning them -- which sounds are clicking, which ones need more reps, whether today's level felt like a stretch or a struggle. It nudges the difficulty in real time, so your child is always in that sweet spot where growth actually happens: challenged, not overwhelmed.",
      "That same living picture -- not a summary, the real thing -- is what your child's speech therapist sees too. So the ten minutes you play together on the couch after dinner aren't separate from therapy. They're quietly part of it.",
      "One thing we want you to feel certain of: everything this app learns about your child exists to help your child. It's never sold, never shared elsewhere -- it stays exactly where it belongs.",
    ],
  },
  therapist: {
    title: 'About this platform',
    accent: 'text-brand-teal',
    body: [
      "Picture having a colleague embedded in every patient's living room, taking notes between sessions -- that's the closest analogy for what this platform does. Every BreathQuest and Chime round is captured in full: sound targeted, score, outcome, self-reported difficulty. Not a parent's recollection of the week -- the actual data.",
      "What makes it genuinely interesting is the adaptive policy engine sitting underneath: it's not a fixed curriculum, it's a model that raises, lowers, or holds difficulty per level in real time, and retrains itself per patient as new sessions come in. The dashboard doesn't just show you the outcome -- it shows you the engine's own reasoning for each adjustment, so you're seeing its logic, not just its output, and can override it the moment your clinical judgment says otherwise.",
      "Open the patient view before a session and you'll already know what's been trending, what's stuck, and what's ready to be pushed -- turning every appointment into a continuation of the story instead of a cold start.",
    ],
  },
}

export default function AboutModal({ role }) {
  const [open, setOpen] = useState(false)
  const content = CONTENT[role] || CONTENT.parent

  useEffect(() => {
    const key = `bq_seen_about_${role}`
    if (!localStorage.getItem(key)) {
      setOpen(true)
      localStorage.setItem(key, '1')
    }
  }, [role])

  useEffect(() => {
    if (!open) return
    const handleKey = (e) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [open])

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="w-full flex items-center gap-3 pl-3 pr-3 py-2.5 rounded-xl text-sm font-medium
                   text-white/55 hover:text-white hover:bg-white/[0.06] transition-colors"
      >
        <Info size={18} className="shrink-0" />
        <span className="truncate">About / How to use</span>
      </button>

      {open && createPortal(
        <div
          className="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm p-4"
          style={{ backgroundColor: 'rgba(0,0,0,0.6)' }}
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-md rounded-3xl bg-[#1B1836] border border-white/10 shadow-2xl p-6 max-h-[85vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className={`font-display text-lg font-bold ${content.accent}`}>{content.title}</h2>
              <button onClick={() => setOpen(false)} className="text-white/65 hover:text-white transition-colors">
                <X size={18} />
              </button>
            </div>
            <div className="flex flex-col gap-3">
              {content.body.map((para, i) => (
                <p key={i} className="text-white/70 text-sm leading-relaxed">{para}</p>
              ))}
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  )
}
