// Shared kid-facing sidebar nav — replaces GameNavbar's APPS list, same
// four games plus "All games" as a way back to the picker. Extracted to
// its own file since it's now used across BreathQuest/Chime/Orpheus/
// Voice Hurdle Race's separate home pages, not owned by any one of them.
import { Home, Wind, Waves, Bell, Rabbit, UserCircle, Layers, Mic, Calendar } from 'lucide-react'

export const KID_SIDEBAR_ITEMS = [
  { label: 'All games',    icon: Home,   to: '/play' },
  // Was only reachable via a single button in GamePicker's header --
  // /play/progress (the weekly practice calendar + goal card) has no
  // sidebar entry anywhere else a kid navigates from.
  { label: 'My Progress',  icon: Calendar, to: '/play/progress' },
  { label: 'BreathQuest',  icon: Wind,   to: '/play/levels' },
  { label: 'Orpheus',      icon: Waves,  to: '/play/vaakmirror' },
  { label: 'Chime',        icon: Bell,   to: '/play/chime' },
  { label: 'Voice Hurdle', icon: Rabbit, to: '/play/voice-hurdle-race' },
  { label: 'Flashcards',   icon: Layers, to: '/play/flashcards' },
  { label: 'Assessment',   icon: Mic,        to: '/assessment' },
  { label: 'My Account',   icon: UserCircle, to: '/play/account' },
]
