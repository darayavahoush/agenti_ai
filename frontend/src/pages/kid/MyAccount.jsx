import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Flame, Star, Calendar, Pencil, Check, X } from 'lucide-react'
import { Avatar, Creature } from '../../components/ui'
import { CREATURE_ACCENTS } from '../../components/ui/Creatures'
import { meAPI } from '../../api/client'
import { useAuth } from '../../context/AuthContext'

const AVATAR_OPTIONS = Object.keys(CREATURE_ACCENTS)

export default function MyAccount() {
  const navigate = useNavigate()
  const { patient, updatePatient } = useAuth()
  const [progress, setProgress] = useState(null)
  const [status, setStatus] = useState('loading') // loading | ready | error

  const [editingName, setEditingName] = useState(false)
  const [nameDraft, setNameDraft] = useState('')
  const [pickingAvatar, setPickingAvatar] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let cancelled = false
    meAPI.progress()
      .then(({ data }) => { if (!cancelled) { setProgress(data); setStatus('ready') } })
      .catch(() => { if (!cancelled) setStatus('error') })
    return () => { cancelled = true }
  }, [])

  const displayName = patient?.first_name || progress?.first_name
  const displayAvatar = patient?.avatar || progress?.avatar

  async function saveProfile(fields) {
    setSaving(true)
    try {
      const { data } = await meAPI.updateProfile(fields)
      // Keep AuthContext's patient object (and localStorage, if
      // AuthContext persists there) in sync so the new name/avatar
      // shows immediately across the app, not just this page.
      updatePatient(data)
    } catch {
      // Swallow -- picker/name field just won't reflect the change;
      // a toast/error banner can be added later if this proves confusing.
    } finally {
      setSaving(false)
    }
  }

  function startEditingName() {
    setNameDraft(displayName || '')
    setEditingName(true)
  }

  async function confirmNameEdit() {
    const trimmed = nameDraft.trim()
    if (trimmed && trimmed !== displayName) {
      await saveProfile({ first_name: trimmed })
    }
    setEditingName(false)
  }

  async function pickAvatar(species) {
    setPickingAvatar(false)
    if (species !== displayAvatar) {
      await saveProfile({ avatar: species })
    }
  }

  const starPct = progress ? Math.min(100, Math.round((progress.total_stars / Math.max(1, progress.max_possible_stars)) * 100)) : 0

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #12142E 0%, #1E1E3F 100%)' }}>
      <div className="max-w-2xl mx-auto px-6 py-10">
        <button
          onClick={() => navigate('/play')}
          className="inline-flex items-center gap-1.5 text-white/40 hover:text-white text-sm mb-8 transition-colors"
        >
          <ArrowLeft size={15} /> Back to games
        </button>

        {status === 'loading' && (
          <div className="text-center py-20 text-white/40">Loading your account…</div>
        )}

        {status === 'error' && (
          <div className="text-center py-20">
            <p className="text-white/50 mb-2">Couldn't load your account right now.</p>
            <p className="text-white/30 text-sm">Try again in a bit!</p>
          </div>
        )}

        {status === 'ready' && progress && (
          <>
            <div className="text-center mb-8">
              <div className="relative inline-block">
                <Avatar avatar={displayAvatar} size="xl" />
                <button
                  onClick={() => setPickingAvatar(true)}
                  className="absolute -bottom-1 -right-1 w-8 h-8 rounded-full bg-white/10 border border-white/20
                             flex items-center justify-center hover:bg-white/20 transition-colors"
                  aria-label="Change avatar"
                >
                  <Pencil size={13} className="text-white/70" />
                </button>
              </div>

              {pickingAvatar && (
                <div className="mt-4 flex justify-center gap-2 flex-wrap">
                  {AVATAR_OPTIONS.map((species) => (
                    <button
                      key={species}
                      onClick={() => pickAvatar(species)}
                      disabled={saving}
                      className={`w-14 h-14 rounded-full p-0.5 transition-all ${
                        species === displayAvatar ? 'ring-2 ring-white/60' : 'opacity-70 hover:opacity-100'
                      }`}
                    >
                      <Creature species={species} className="w-full h-full" />
                    </button>
                  ))}
                  <button
                    onClick={() => setPickingAvatar(false)}
                    className="text-white/30 hover:text-white/60 text-xs ml-1 self-center"
                  >
                    Done
                  </button>
                </div>
              )}

              <div className="mt-5 flex items-center justify-center gap-2">
                {editingName ? (
                  <>
                    <input
                      autoFocus
                      value={nameDraft}
                      onChange={(e) => setNameDraft(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') confirmNameEdit(); if (e.key === 'Escape') setEditingName(false) }}
                      maxLength={30}
                      className="font-vm-display text-3xl font-bold text-white bg-white/5 border border-white/20
                                 rounded-xl px-3 py-1 text-center focus:outline-none focus:border-white/40"
                    />
                    <button onClick={confirmNameEdit} disabled={saving} className="text-brand-green hover:text-brand-green/70">
                      <Check size={20} />
                    </button>
                    <button onClick={() => setEditingName(false)} className="text-white/30 hover:text-white/60">
                      <X size={20} />
                    </button>
                  </>
                ) : (
                  <>
                    <h1 className="font-vm-display text-3xl font-bold text-white">
                      {displayName}
                    </h1>
                    <button onClick={startEditingName} className="text-white/25 hover:text-white/60 transition-colors" aria-label="Edit name">
                      <Pencil size={15} />
                    </button>
                  </>
                )}
              </div>
              <p className="text-white/40 mt-2">Look how far you've come! 🎉</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
              <div className="rounded-2xl p-6 text-center border border-white/10 bg-white/5">
                <div className="w-12 h-12 rounded-full bg-ember/15 flex items-center justify-center mx-auto mb-3">
                  <Flame className="w-6 h-6 text-ember" />
                </div>
                <p className="font-vm-display text-3xl font-bold text-white">{progress.current_streak_days}</p>
                <p className="text-white/40 text-xs mt-1">
                  day{progress.current_streak_days === 1 ? '' : 's'} in a row
                </p>
              </div>

              <div className="rounded-2xl p-6 text-center border border-white/10 bg-white/5">
                <div className="w-12 h-12 rounded-full bg-mint/15 flex items-center justify-center mx-auto mb-3">
                  <Calendar className="w-6 h-6 text-mint" />
                </div>
                <p className="font-vm-display text-3xl font-bold text-white">{progress.games_played_this_week}</p>
                <p className="text-white/40 text-xs mt-1">
                  game{progress.games_played_this_week === 1 ? '' : 's'} this week
                </p>
              </div>

              <div className="rounded-2xl p-6 text-center border border-white/10 bg-white/5">
                <div className="w-12 h-12 rounded-full bg-brand-amber/15 flex items-center justify-center mx-auto mb-3">
                  <Star className="w-6 h-6 text-brand-amber" fill="currentColor" fillOpacity={0.3} />
                </div>
                <p className="font-vm-display text-3xl font-bold text-white">{progress.total_stars}</p>
                <p className="text-white/40 text-xs mt-1">total stars</p>
              </div>
            </div>

            <div className="rounded-2xl p-6 border border-white/10 bg-white/5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-white/60 text-sm font-medium">Stars earned</span>
                <span className="text-white/40 text-xs">
                  {progress.total_stars} / {progress.max_possible_stars}
                </span>
              </div>
              <div className="h-3 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-brand-amber to-ember rounded-full transition-[width] duration-700"
                  style={{ width: `${starPct}%` }}
                />
              </div>
              {starPct === 100 && (
                <p className="text-brand-amber text-xs font-semibold mt-3 text-center">
                  🏆 You've earned every star — amazing!
                </p>
              )}
            </div>

            {progress.current_streak_days === 0 && (
              <p className="text-white/30 text-xs text-center mt-8">
                Play a game today to start a new streak!
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
