import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ArrowLeft, Flame, Star, Calendar, Pencil, Check, X, History, Camera } from 'lucide-react'
import { Avatar } from '../../components/ui'
import { Creature, CREATURE_ACCENTS } from '../../components/ui/Creatures'
import { meAPI, getErrorMessage } from '../../api/client'
import PhotoCropModal from './PhotoCropModal'
import { useAuth } from '../../context/AuthContext'
import { Trash2 } from 'lucide-react'

const AVATAR_OPTIONS = Object.keys(CREATURE_ACCENTS)

export default function MyAccount() {
  const navigate = useNavigate()
  const { patient, updatePatient, deleteKidAccount } = useAuth()
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [progress, setProgress] = useState(null)
  const [status, setStatus] = useState('loading') // loading | ready | error

  const [editingName, setEditingName] = useState(false)
  const [nameDraft, setNameDraft] = useState('')
  const [pickingAvatar, setPickingAvatar] = useState(false)
  const [saving, setSaving] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [profileError, setProfileError] = useState('')
  const [cropImageSrc, setCropImageSrc] = useState(null)
  const [deleteError, setDeleteError] = useState('')
  const [deletePin, setDeletePin] = useState('')

  const [changingPin, setChangingPin] = useState(false)
  const [currentPinDraft, setCurrentPinDraft] = useState('')
  const [newPinDraft, setNewPinDraft] = useState('')
  const [pinSaving, setPinSaving] = useState(false)
  const [pinError, setPinError] = useState('')
  const [pinChanged, setPinChanged] = useState(false)

  const fetchProgress = () => {
    setStatus('loading')
    let cancelled = false
    meAPI.progress()
      .then(({ data }) => { if (!cancelled) { setProgress(data); setStatus('ready') } })
      .catch(() => { if (!cancelled) setStatus('error') })
    return () => { cancelled = true }
  }

  useEffect(() => fetchProgress(), [])

  const displayName = patient?.first_name || progress?.first_name
  const displayAvatar = patient?.avatar || progress?.avatar
  const displayPhotoUrl = patient?.avatar_photo_url
  // Photo, if uploaded, takes visual priority over the creature species art
  const apiBase = (import.meta.env.VITE_API_URL || '').replace(/\/api\/v1$/, '')

  function handlePhotoSelect(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadError('')
    setCropImageSrc(URL.createObjectURL(file))
    e.target.value = ''
  }

  function cancelCrop() {
    if (cropImageSrc) URL.revokeObjectURL(cropImageSrc)
    setCropImageSrc(null)
  }

  async function confirmCrop(blob) {
    setSaving(true)
    try {
      const croppedFile = new File([blob], 'avatar.jpg', { type: 'image/jpeg' })
      const { data } = await meAPI.uploadProfilePhoto(croppedFile)
      updatePatient(data)
      setPickingAvatar(false)
    } catch (err) {
      setUploadError(getErrorMessage(err, "Couldn't upload that photo -- try a different one."))
    } finally {
      setSaving(false)
      cancelCrop()
    }
  }

  async function saveProfile(fields) {
    setSaving(true)
    setProfileError('')
    try {
      const { data } = await meAPI.updateProfile(fields)
      // Keep AuthContext's patient object (and localStorage, if
      // AuthContext persists there) in sync so the new name/avatar
      // shows immediately across the app, not just this page.
      updatePatient(data)
      return true
    } catch {
      setProfileError("Couldn't save that -- try again.")
      return false
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
      const ok = await saveProfile({ first_name: trimmed })
      if (!ok) return // keep the editor open so they can retry without retyping
      toast.success('Name saved!')
    }
    setEditingName(false)
  }

  async function pickAvatar(species) {
    setPickingAvatar(false)
    if (species !== displayAvatar) {
      await saveProfile({ avatar: species })
    }
  }

  async function confirmPinChange() {
    setPinError('')
    if (!/^\d{4}$/.test(currentPinDraft) || !/^\d{4}$/.test(newPinDraft)) {
      setPinError('PINs must be exactly 4 digits.')
      return
    }
    setPinSaving(true)
    try {
      await meAPI.changePin({ current_pin: currentPinDraft, new_pin: newPinDraft })
      setChangingPin(false)
      setCurrentPinDraft('')
      setNewPinDraft('')
      setPinChanged(true)
      setTimeout(() => setPinChanged(false), 3000)
    } catch (err) {
      setPinError(getErrorMessage(err, "Couldn't change your PIN -- check your current PIN and try again."))
    } finally {
      setPinSaving(false)
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
            <button
              onClick={fetchProgress}
              className="text-white/60 hover:text-white text-sm underline underline-offset-2 transition-colors"
            >
              Try again
            </button>
          </div>
        )}

        {status === 'ready' && progress && (
          <>
            <div className="text-center mb-8">
              <div className="relative inline-block">
                {displayPhotoUrl ? (
                  <img
                    src={`${apiBase}${displayPhotoUrl}`}
                    alt="Your profile photo"
                    className="w-24 h-24 rounded-full object-cover border-2 border-white/10"
                  />
                ) : (
                  <Avatar avatar={displayAvatar} photoUrl={displayPhotoUrl} size="xl" />
                )}
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
                  <label
                    className="relative w-14 h-14 rounded-full flex items-center justify-center cursor-pointer
                               border-2 transition-all duration-200 hover:scale-110 active:scale-95 group"
                    style={{
                      borderColor: 'rgba(168,255,111,0.5)',
                      background: 'linear-gradient(160deg, rgba(168,255,111,0.22) 0%, rgba(30,30,63,0.5) 100%)',
                      boxShadow: '0 0 0 rgba(168,255,111,0)',
                    }}
                  >
                    <div className="absolute inset-0 rounded-full motion-safe:animate-pulse-slow"
                         style={{ boxShadow: '0 0 12px 2px rgba(168,255,111,0.35)' }} />
                    <input type="file" accept="image/*" onChange={handlePhotoSelect} className="hidden" disabled={saving} />
                    <Camera size={20} className="relative text-[#A8FF6F] group-hover:scale-110 transition-transform" />
                  </label>
                  <button
                    onClick={() => setPickingAvatar(false)}
                    className="text-white/30 hover:text-white/60 text-xs ml-1 self-center"
                  >
                    Done
                  </button>
                </div>
              )}
              {uploadError && (
                <p className="text-brand-amber text-xs mt-2 text-center">{uploadError}</p>
              )}
              {profileError && (
                <p className="text-brand-amber text-xs mt-2 text-center">{profileError}</p>
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
                    <button onClick={confirmNameEdit} disabled={saving} className="text-brand-green hover:text-brand-green/70" aria-label="Save name">
                      <Check size={20} />
                    </button>
                    <button onClick={() => setEditingName(false)} className="text-white/30 hover:text-white/60" aria-label="Cancel editing name">
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

            <button
              onClick={() => navigate('/play/account/history')}
              className="w-full mt-4 rounded-2xl p-4 border border-white/10 bg-white/5 hover:bg-white/10
                         flex items-center justify-between transition-colors group"
            >
              <span className="flex items-center gap-3">
                <span className="w-9 h-9 rounded-full bg-sky/15 flex items-center justify-center">
                  <History className="w-4 h-4 text-sky" />
                </span>
                <span className="text-white text-sm font-medium">My History</span>
              </span>
              <span className="text-white/30 text-xs group-hover:text-white/50 transition-colors">
                Assessments &amp; games →
              </span>
            </button>

            {progress.current_streak_days === 0 && (
              <p className="text-white/30 text-xs text-center mt-8">
                Play a game today to start a new streak!
              </p>
            )}
          </>
        )}
      </div>
      {/* Change PIN -- previously the only way to get a new PIN was to
          pretend it was forgotten and go through the parent-email OTP
          recovery flow. This is for "I just want a new one", using the
          current PIN as re-auth instead. */}
      <div className="mt-12 pt-6 border-t border-white/10">
        {!changingPin ? (
          <div className="text-center">
            <button onClick={() => { setChangingPin(true); setPinError('') }}
                    className="text-white/40 hover:text-white text-xs mx-auto transition-colors">
              Change my PIN
            </button>
            {pinChanged && <p className="text-mint text-xs mt-2">PIN changed!</p>}
          </div>
        ) : (
          <div className="text-center max-w-xs mx-auto">
            <p className="text-white/50 text-sm mb-3">Enter your current PIN and pick a new one.</p>
            <input
              type="password" inputMode="numeric" maxLength={4} autoComplete="off"
              value={currentPinDraft}
              onChange={(e) => setCurrentPinDraft(e.target.value.replace(/\D/g, '').slice(0, 4))}
              placeholder="Current PIN"
              className="w-full mb-2 text-center tracking-[0.5em] px-4 py-2.5 rounded-xl bg-white/5 border border-white/10
                         text-white text-sm placeholder:text-white/30 placeholder:tracking-normal focus:outline-none focus:border-mint/40"
            />
            <input
              type="password" inputMode="numeric" maxLength={4} autoComplete="off"
              value={newPinDraft}
              onChange={(e) => setNewPinDraft(e.target.value.replace(/\D/g, '').slice(0, 4))}
              placeholder="New PIN"
              className="w-full mb-2 text-center tracking-[0.5em] px-4 py-2.5 rounded-xl bg-white/5 border border-white/10
                         text-white text-sm placeholder:text-white/30 placeholder:tracking-normal focus:outline-none focus:border-mint/40"
            />
            {pinError && <p className="text-brand-coral text-xs mb-3">{pinError}</p>}
            <div className="flex items-center justify-center gap-3">
              <button onClick={() => { setChangingPin(false); setCurrentPinDraft(''); setNewPinDraft(''); setPinError('') }}
                      className="text-white/40 hover:text-white/70 text-sm px-4 py-2 transition-colors">
                Never mind
              </button>
              <button
                disabled={pinSaving || currentPinDraft.length !== 4 || newPinDraft.length !== 4}
                onClick={confirmPinChange}
                className="text-mint hover:text-white text-sm font-semibold px-4 py-2 rounded-xl
                           bg-mint/10 hover:bg-mint/30 border border-mint/30 transition-colors disabled:opacity-50">
                {pinSaving ? 'Saving…' : 'Save new PIN'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Delete account -- two-tap confirm, since this is destructive and
          irreversible (deletes all game progress, not just the login). */}
      <div className="mt-12 pt-6 border-t border-white/10">
        {!confirmingDelete ? (
          <button onClick={() => setConfirmingDelete(true)}
                  className="text-white/25 hover:text-brand-coral text-xs flex items-center gap-1.5 mx-auto transition-colors">
            <Trash2 className="w-3.5 h-3.5" /> Delete my account
          </button>
        ) : (
          <div className="text-center">
            <p className="text-white/50 text-sm mb-3">
              This deletes everything — your progress, stars, all of it. Are you sure?
            </p>
            <input
              type="password" inputMode="numeric" maxLength={4} autoComplete="off"
              value={deletePin}
              onChange={(e) => { setDeletePin(e.target.value.replace(/\D/g, '').slice(0, 4)); setDeleteError('') }}
              placeholder="Enter your PIN to confirm"
              className="w-full max-w-xs mx-auto mb-3 text-center tracking-[0.5em] px-4 py-2.5 rounded-xl bg-white/5
                         border border-white/10 text-white text-sm placeholder:text-white/30 placeholder:tracking-normal
                         focus:outline-none focus:border-brand-coral/40"
            />
            <div className="flex items-center justify-center gap-3">
              <button onClick={() => { setConfirmingDelete(false); setDeletePin(''); setDeleteError('') }}
                      className="text-white/40 hover:text-white/70 text-sm px-4 py-2 transition-colors">
                Never mind
              </button>
              <button
                disabled={deleting || deletePin.length !== 4}
                onClick={async () => {
                  setDeleting(true)
                  setDeleteError('')
                  try {
                    await deleteKidAccount(deletePin)
                    navigate('/')
                  } catch (err) {
                    setDeleteError(getErrorMessage(err, "Couldn't delete your account -- try again."))
                    setDeleting(false)
                  }
                }}
                className="text-brand-coral hover:text-white text-sm font-semibold px-4 py-2 rounded-xl
                           bg-brand-coral/10 hover:bg-brand-coral border border-brand-coral/30 transition-colors disabled:opacity-50">
                {deleting ? 'Deleting…' : 'Yes, delete it'}
              </button>
            </div>
            {deleteError && (
              <p className="text-brand-coral text-xs mt-3">{deleteError}</p>
            )}
          </div>
        )}
      </div>

      {cropImageSrc && (
        <PhotoCropModal
          imageSrc={cropImageSrc}
          onCancel={cancelCrop}
          onConfirm={confirmCrop}
          saving={saving}
        />
      )}
    </div>
  )
}
