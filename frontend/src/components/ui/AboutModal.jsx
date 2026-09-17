import { Link } from 'react-router-dom'
import { Info, Wind, Brain, Star, Gamepad2, Eye, ShieldCheck, Home, Settings2, ClipboardCheck } from 'lucide-react'

// About/How-it-works content, now a real page per role (see AboutPage.jsx)
// instead of a modal -- kept here since AboutModal.jsx already owned the
// role-specific copy, and this keeps that copy in one place regardless of
// which component renders it. Content is broken into titled sections (was
// flat paragraphs) so the page reads as structured sections rather than a
// wall of text.
export const ABOUT_CONTENT = {
  kid: {
    title: 'Welcome, sound explorer! 🚀',
    accent: 'text-[#FF9B54]',
    accentBg: 'bg-[#FF9B54]/15 border-[#FF9B54]/25',
    sections: [
      {
        heading: 'Your breath is magic fuel',
        icon: Wind,
        body: "Did you know your breath is actually magic fuel? Every time you play Pinwheel Spin, you're training your lungs like a superhero trains their powers -- stronger breath means stronger, clearer words.",
      },
      {
        heading: 'This app is watching you play',
        icon: Brain,
        body: "And here's the wildest part: this app is basically watching you play and thinking, in real time, just like a coach would. Get something tricky? It quietly makes the next round a little gentler. Crushing it? It turns up the fun. It's adjusting itself around YOU, every single time -- nobody else in the world gets that exact game.",
      },
      {
        heading: 'Building a trail of awesome',
        icon: Star,
        body: "Every sound you practice, every level you beat -- it all lights up on a screen your grown-up and your speech therapist can see. You're not just playing a game. You're building a trail of awesome for them to follow and cheer about.",
      },
    ],
  },
  parent: {
    title: 'The story behind this app',
    accent: 'text-coral-light',
    accentBg: 'bg-coral/15 border-coral/25',
    sections: [
      {
        heading: 'Games kids actually want to play',
        icon: Gamepad2,
        body: "Here's the idea we started with: kids don't practice things because they're told to -- they practice things because they're fun. So instead of speech drills, we built games your child actually wants to come back to, and hid the practice inside the play.",
      },
      {
        heading: "What's happening underneath",
        icon: Brain,
        body: "The more interesting part is what's happening underneath. Every round your child plays feeds a system that's genuinely learning them -- which sounds are clicking, which ones need more reps, whether today's level felt like a stretch or a struggle. It nudges the difficulty in real time, so your child is always in that sweet spot where growth actually happens: challenged, not overwhelmed.",
      },
      {
        heading: 'The same picture your therapist sees',
        icon: Eye,
        body: "That same living picture -- not a summary, the real thing -- is what your child's speech therapist sees too. So the ten minutes you play together on the couch after dinner aren't separate from therapy. They're quietly part of it.",
      },
      {
        heading: "Your child's data, always protected",
        icon: ShieldCheck,
        body: "One thing we want you to feel certain of: everything this app learns about your child exists to help your child. It's never sold, never shared elsewhere -- it stays exactly where it belongs.",
      },
    ],
  },
  therapist: {
    title: 'About this platform',
    accent: 'text-brand-teal',
    accentBg: 'bg-brand-teal/15 border-brand-teal/25',
    sections: [
      {
        heading: 'A colleague in every living room',
        icon: Home,
        body: "Picture having a colleague embedded in every patient's living room, taking notes between sessions -- that's the closest analogy for what this platform does. Every BreathQuest and Chime round is captured in full: sound targeted, score, outcome, self-reported difficulty. Not a parent's recollection of the week -- the actual data.",
      },
      {
        heading: 'The adaptive policy engine underneath',
        icon: Settings2,
        body: "What makes it genuinely interesting is the adaptive policy engine sitting underneath: it's not a fixed curriculum, it's a model that raises, lowers, or holds difficulty per level in real time, and retrains itself per patient as new sessions come in. The dashboard doesn't just show you the outcome -- it shows you the engine's own reasoning for each adjustment, so you're seeing its logic, not just its output, and can override it the moment your clinical judgment says otherwise.",
      },
      {
        heading: 'Walk into every session prepared',
        icon: ClipboardCheck,
        body: "Open the patient view before a session and you'll already know what's been trending, what's stuck, and what's ready to be pushed -- turning every appointment into a continuation of the story instead of a cold start.",
      },
    ],
  },
}

export const ABOUT_PATH = { kid: '/play/about', parent: '/parent/about', therapist: '/therapist/about' }

// Sidebar footer link -- was a button that opened a modal in place; now a
// plain link out to the full About page for this role. Kept the same
// component name/prop (role) as the old modal so every existing call site
// (GamePicker, ParentDashboard, both Settings pages, Dashboard, etc.) needs
// no changes at all.
export default function AboutModal({ role }) {
  const unseen = typeof window !== 'undefined' && !localStorage.getItem(`bq_seen_about_${role}`)

  return (
    <Link
      to={ABOUT_PATH[role] || ABOUT_PATH.parent}
      className="w-full flex items-center gap-3 pl-3 pr-3 py-2.5 rounded-xl text-sm font-medium
                 text-white/55 hover:text-white hover:bg-white/[0.06] transition-colors"
    >
      <Info size={18} className="shrink-0" />
      <span className="truncate flex-1">About / How to use</span>
      {unseen && <span className="w-1.5 h-1.5 rounded-full bg-brand-green shrink-0" />}
    </Link>
  )
}
