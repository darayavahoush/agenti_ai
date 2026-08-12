#!/usr/bin/env python3
"""
Run from inside agenti_ai. Wires the new Sidebar into TherapistDashboard,
PatientDetail, and ParentDashboard.
"""
import pathlib

ROOT = pathlib.Path("quest-games/breathquest/frontend/src")

def patch(path, replacements, label):
    p = ROOT / path
    text = p.read_text()
    for old, new in replacements:
        if old not in text:
            raise SystemExit(f"[{label}] MATCH NOT FOUND — aborting before touching {p}.\n"
                              f"--- expected to find ---\n{old[:300]}...")
        count = text.count(old)
        if count != 1:
            raise SystemExit(f"[{label}] Expected exactly 1 match, found {count} — aborting {p}.")
        text = text.replace(old, new)
    p.write_text(text)
    print(f"[{label}] patched {p}")


# ---------------------------------------------------------------- Dashboard.jsx
patch(
    "pages/therapist/Dashboard.jsx",
    [
        (
            "import { Button, Card, Badge, Avatar, StatCard, PageLoader } from '../../components/ui'",
            "import { Button, Card, Badge, Avatar, StatCard, PageLoader, Sidebar } from '../../components/ui'",
        ),
        (
            "import {\n  Wind, Users, UserCheck, Gamepad2, Star, AlertTriangle, Clock,\n  Search, ArrowUpDown, Sparkles, UserPlus, ChevronRight,\n} from 'lucide-react'",
            "import {\n  Users, UserCheck, Gamepad2, Star, AlertTriangle, Clock,\n  Search, ArrowUpDown, Sparkles, UserPlus, ChevronRight, LayoutDashboard,\n} from 'lucide-react'",
        ),
        (
            """  return (
    <div className="min-h-screen relative"
         style={{ background: 'radial-gradient(ellipse 1400px 800px at 15% -10%, #1D9E75 0%, #16332D 35%, #12122A 70%)' }}>
      {/* A real gradient now, not just a couple of faint blur blobs on a flat
          fill — same idea as the login screen's radial panel, in the
          brand.teal/brand.dark this page (and PatientDetail) already use. */}
      <div className="absolute -top-32 right-0 w-96 h-96 rounded-full bg-brand-green/10 blur-3xl pointer-events-none" />

      {/* Top nav */}
      <nav className="relative border-b border-white/10 px-6 py-4 flex items-center justify-between sticky top-0 bg-brand-dark/90 backdrop-blur z-10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-brand-teal/15 border border-brand-teal/25 flex items-center justify-center">
            <Wind size={18} className="text-brand-teal" />
          </div>
          <span className="font-display text-xl font-bold text-white">
            Breath<span className="text-brand-green">Quest</span>
          </span>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-white text-sm font-medium leading-tight">{therapist?.full_name}</p>
            {therapist?.clinic_name && (
              <p className="text-white/35 text-xs leading-tight">{therapist.clinic_name}</p>
            )}
          </div>
          <div className="w-px h-8 bg-white/10" />
          <Button variant="ghost" size="sm" onClick={logout}>Sign out</Button>
        </div>
      </nav>

      <div className="relative max-w-6xl mx-auto px-6 py-8">""",
            """  return (
    <div className="min-h-screen relative flex"
         style={{ background: 'radial-gradient(ellipse 1400px 800px at 15% -10%, #1D9E75 0%, #16332D 35%, #12122A 70%)' }}>
      {/* A real gradient now, not just a couple of faint blur blobs on a flat
          fill — same idea as the login screen's radial panel, in the
          brand.teal/brand.dark this page (and PatientDetail) already use. */}
      <div className="absolute -top-32 right-0 w-96 h-96 rounded-full bg-brand-green/10 blur-3xl pointer-events-none" />

      <Sidebar
        role="therapist"
        items={[
          { label: 'Dashboard', icon: LayoutDashboard, to: '/therapist/dashboard' },
        ]}
        name={therapist?.full_name}
        subtitle={therapist?.clinic_name}
        onLogout={logout}
      />

      <div className="relative flex-1 min-w-0 max-w-6xl mx-auto px-6 py-8">""",
        ),
    ],
    "Dashboard.jsx",
)

# ------------------------------------------------------------- PatientDetail.jsx
patch(
    "pages/therapist/PatientDetail.jsx",
    [
        (
            "import { useParams, useNavigate } from 'react-router-dom'",
            "import { useParams, useNavigate } from 'react-router-dom'\nimport { useAuth } from '../../context/AuthContext'",
        ),
        (
            "import { Card, Badge, Avatar, StarRating, Button, Spinner, PageLoader } from '../../components/ui'",
            "import { Card, Badge, Avatar, StarRating, Button, Spinner, PageLoader, Sidebar } from '../../components/ui'",
        ),
        (
            "import { Download, BarChart3, Gamepad2, Dog, Bell, Waves, HeartPulse, FileText } from 'lucide-react'",
            "import { Download, BarChart3, Gamepad2, Dog, Bell, Waves, HeartPulse, FileText, LayoutDashboard } from 'lucide-react'",
        ),
        (
            "export default function PatientDetail() {\n  const { id } = useParams()\n  const navigate = useNavigate()",
            "export default function PatientDetail() {\n  const { id } = useParams()\n  const navigate = useNavigate()\n  const { therapist, logout } = useAuth()",
        ),
        (
            """  return (
    <div className="min-h-screen bg-brand-dark relative">
      {/* Same ambient glow as the therapist dashboard, so landing on a
          specific patient doesn't feel like a flatter, less-considered
          page than the dashboard just navigated from. */}
      <div className="absolute top-0 left-0 w-full h-80 overflow-hidden pointer-events-none">
        <div className="absolute -top-32 -left-24 w-[28rem] h-[28rem] rounded-full bg-brand-teal/[0.07] blur-[100px]" />
        <div className="absolute -top-40 right-0 w-[26rem] h-[26rem] rounded-full bg-brand-green/[0.05] blur-[100px]" />
      </div>

      {/* Nav */}""",
            """  return (
    <div className="min-h-screen bg-brand-dark relative flex">
      {/* Same ambient glow as the therapist dashboard, so landing on a
          specific patient doesn't feel like a flatter, less-considered
          page than the dashboard just navigated from. */}
      <div className="absolute top-0 left-0 w-full h-80 overflow-hidden pointer-events-none">
        <div className="absolute -top-32 -left-24 w-[28rem] h-[28rem] rounded-full bg-brand-teal/[0.07] blur-[100px]" />
        <div className="absolute -top-40 right-0 w-[26rem] h-[26rem] rounded-full bg-brand-green/[0.05] blur-[100px]" />
      </div>

      <Sidebar
        role="therapist"
        items={[
          { label: 'Dashboard', icon: LayoutDashboard, to: '/therapist/dashboard' },
        ]}
        name={therapist?.full_name}
        subtitle={therapist?.clinic_name}
        onLogout={logout}
      />

      <div className="relative flex-1 min-w-0">
      {/* Nav */}""",
        ),
        (
            """            {notes.length === 0 && (
              <Card className="text-center py-12 text-white/40">No notes yet</Card>
            )}
          </div>
        )}
      </div>
    </div>
  )
}""",
            """            {notes.length === 0 && (
              <Card className="text-center py-12 text-white/40">No notes yet</Card>
            )}
          </div>
        )}
      </div>
      </div>
    </div>
  )
}""",
        ),
    ],
    "PatientDetail.jsx",
)

# ------------------------------------------------------------ ParentDashboard.jsx
patch(
    "pages/parent/ParentDashboard.jsx",
    [
        (
            "import { Avatar, Card, StatCard } from '../../components/ui'",
            "import { Avatar, Card, StatCard, Sidebar } from '../../components/ui'",
        ),
        (
            """  return (
    <div className="min-h-screen bg-ink relative">
      {/* Ambient glow header — same elevated-dashboard language as the
          therapist side, in the parent flow's own coral/mint accent pair
          instead of teal/green. */}
      <div className="absolute top-0 left-0 w-full h-80 overflow-hidden pointer-events-none">
        <div className="absolute -top-32 -left-24 w-[28rem] h-[28rem] rounded-full bg-coral/[0.08] blur-[100px]" />
        <div className="absolute -top-40 right-0 w-[26rem] h-[26rem] rounded-full bg-mint/[0.06] blur-[100px]" />
      </div>

      <div className="relative flex items-center justify-between px-6 py-4 border-b border-white/[0.08]
                       sticky top-0 bg-ink/85 backdrop-blur-xl z-10">
        <div className="flex items-center gap-3">
          <Avatar avatar={data?.avatar} size="sm" />
          <span className="font-display font-bold text-paper">
            {data?.child_first_name || parent?.child_first_name}'s Progress
          </span>
        </div>
        <button onClick={logout} className="flex items-center gap-1.5 text-paper/40 hover:text-paper/70 text-sm transition-colors">
          <LogOut size={14} /> Log out
        </button>
      </div>

      <div className="relative max-w-3xl mx-auto px-6 py-10">""",
            """  return (
    <div className="min-h-screen bg-ink relative flex">
      {/* Ambient glow header — same elevated-dashboard language as the
          therapist side, in the parent flow's own coral/mint accent pair
          instead of teal/green. */}
      <div className="absolute top-0 left-0 w-full h-80 overflow-hidden pointer-events-none">
        <div className="absolute -top-32 -left-24 w-[28rem] h-[28rem] rounded-full bg-coral/[0.08] blur-[100px]" />
        <div className="absolute -top-40 right-0 w-[26rem] h-[26rem] rounded-full bg-mint/[0.06] blur-[100px]" />
      </div>

      <Sidebar
        role="parent"
        items={[
          { label: 'Progress', icon: TrendingUp, to: '/parent/dashboard' },
        ]}
        name={(data?.child_first_name || parent?.child_first_name) ? `${data?.child_first_name || parent?.child_first_name}'s Progress` : undefined}
        onLogout={logout}
      />

      <div className="relative flex-1 min-w-0 max-w-3xl mx-auto px-6 py-10">""",
        ),
        (
            """            <p className="text-paper/25 text-xs text-center mt-10">
              Showing BreathQuest progress. Ask your child's therapist about progress in other games.
            </p>
          </>
        )}
      </div>
    </div>
  )
}""",
            """            <p className="text-paper/25 text-xs text-center mt-10">
              Showing BreathQuest progress. Ask your child's therapist about progress in other games.
            </p>
          </>
        )}
      </div>
      </div>
    </div>
  )
}""",
        ),
    ],
    "ParentDashboard.jsx",
)

print("\nAll three pages patched.")
