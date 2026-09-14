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
    title: 'What is this app?',
    accent: 'text-[#FF9B54]',
    body: [
      "This app has games that help you practice your sounds!",
      "Every time you play, it's like a little workout for your speech -- the games get a bit harder or easier depending on how you're doing, so it should always feel like a fun challenge, not too easy and not too hard.",
      "Your grown-up and your speech therapist can see how your practice is going, so they know what to celebrate with you and what to help you with next.",
    ],
  },
  parent: {
    title: 'About this app',
    accent: 'text-coral-light',
    body: [
      "BreathQuest and the Chime games are speech-practice games your child plays. Each session logs things like which sounds were practiced, how they scored, and whether a level felt too easy or too hard.",
      "That data feeds an adaptive difficulty system, so the games automatically stay at a good challenge level for your child instead of staying static.",
      "Your child's speech therapist can see this same progress data, which helps them tailor real sessions around what's actually happening at home, not just what happens in the clinic.",
      "We only use this data to support your child's practice and therapy -- it's not shared or sold anywhere else.",
    ],
  },
  therapist: {
    title: 'About this platform',
    accent: 'text-brand-teal',
    body: [
      "Every gameplay event from a patient's BreathQuest and Chime sessions is logged with the sound/level practiced, score, attempt outcome, and self-reported difficulty signals.",
      "An adaptive policy engine uses that stream to raise, lower, or hold difficulty per level in real time, and periodically retrains per-patient as more data comes in -- you're seeing the same recommendations the game itself is acting on.",
      "Use the patient dashboard to review trends, flag targeted sounds from a diagnostic assessment, and see the agent's own reasoning (raise/lower/hold + message) behind each adjustment, so you can decide whether to intervene manually.",
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
