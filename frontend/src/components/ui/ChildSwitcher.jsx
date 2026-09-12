import { useState, useEffect } from 'react'
import { X, Check, Plus, Link2, ArrowLeftRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '../../context/AuthContext'
import { getErrorMessage } from '../../api/client'
import { Avatar } from './index'

const AVATAR_OPTIONS = ['chick', 'dragon', 'bunny', 'fox', 'rocket', 'fish']

// Trigger + modal in one component, deliberately self-contained (owns its
// own open/closed state) so any parent-facing page can drop it into
// Sidebar's extraFooter slot without each page having to manage a
// switcher-open boolean itself. Renders nothing for roles other than
// parent, and nothing until childrenList has loaded at least once.
export default function ChildSwitcher() {
  const { parent, childrenList, switchChild, addChild, linkChild } = useAuth()
  const [open, setOpen] = useState(false)
  const [view, setView] = useState('list') // 'list' | 'add' | 'link'
  const [busy, setBusy] = useState(false)
  const [addForm, setAddForm] = useState({ firstName: '', avatar: 'chick', pin: '' })
  const [linkCode, setLinkCode] = useState('')

  if (!parent) return null

  const activeChild = childrenList.find((c) => c.is_active)
  const close = () => { setOpen(false); setView('list') }

  // Escape closes the modal, matching the click-outside-to-dismiss backdrop
  // -- without this, keyboard-only users have no way to back out.
  useEffect(() => {
    if (!open) return
    const handleKey = (e) => { if (e.key === 'Escape') close() }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [open])

  const handleSwitch = async (child) => {
    if (child.is_active) { close(); return }
    setBusy(true)
    try {
      await switchChild(child.patient_id)
      toast.success(`Switched to ${child.first_name}`)
      close()
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't switch child"))
    } finally {
      setBusy(false)
    }
  }

  const handleAdd = async (e) => {
    e.preventDefault()
    if (!addForm.firstName.trim() || !/^\d{4}$/.test(addForm.pin)) {
      toast.error("Enter a name and a 4-digit PIN")
      return
    }
    setBusy(true)
    try {
      const child = await addChild(addForm)
      toast.success(`${child.first_name} added`)
      setAddForm({ firstName: '', avatar: 'chick', pin: '' })
      setView('list')
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't add child"))
    } finally {
      setBusy(false)
    }
  }

  const handleLink = async (e) => {
    e.preventDefault()
    if (!linkCode.trim()) return
    setBusy(true)
    try {
      const child = await linkChild(linkCode.trim())
      toast.success(`${child.first_name} added`)
      setLinkCode('')
      setView('list')
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't find that code"))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium
                   text-paper/55 hover:text-paper hover:bg-white/[0.06] transition-colors"
      >
        <ArrowLeftRight size={14} className="shrink-0" />
        <span className="truncate">
          {childrenList.length > 1 ? 'Switch child' : 'Manage children'}
        </span>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={close}
        >
          <div
            className="w-full max-w-sm rounded-3xl bg-[#1B1836] border border-white/10 shadow-2xl p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-paper font-display text-lg font-bold">
                {view === 'list' && 'Your children'}
                {view === 'add' && 'Add a child'}
                {view === 'link' && 'Link a child'}
              </h2>
              <button onClick={close} className="text-paper/65 hover:text-paper transition-colors">
                <X size={18} />
              </button>
            </div>

            {view === 'list' && (
              <>
                <div className="flex flex-col gap-2 mb-4 max-h-72 overflow-y-auto">
                  {childrenList.map((child) => (
                    <button
                      key={child.patient_id}
                      disabled={busy}
                      onClick={() => handleSwitch(child)}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-2xl border transition-colors text-left
                                  disabled:opacity-50
                                  ${child.is_active
                                    ? 'bg-coral/15 border-coral/30'
                                    : 'bg-white/[0.03] border-white/10 hover:bg-white/[0.06]'}`}
                    >
                      <Avatar avatar={child.avatar} photoUrl={child.avatar_photo_url} size="sm" name={child.first_name} />
                      <div className="flex-1 min-w-0">
                        <p className="text-paper text-sm font-medium truncate">{child.first_name}</p>
                        {child.is_primary && <p className="text-paper/40 text-[11px]">Primary</p>}
                      </div>
                      {child.is_active && <Check size={16} className="text-coral-light shrink-0" />}
                    </button>
                  ))}
                </div>
                <div className="flex flex-col gap-2">
                  <button
                    onClick={() => setView('add')}
                    className="flex items-center gap-2 px-3 py-2.5 rounded-2xl border border-dashed border-white/15
                               text-paper/60 hover:text-paper hover:border-white/30 transition-colors text-sm font-medium"
                  >
                    <Plus size={16} /> Add another child
                  </button>
                  <button
                    onClick={() => setView('link')}
                    className="flex items-center gap-2 px-3 py-2.5 rounded-2xl border border-dashed border-white/15
                               text-paper/60 hover:text-paper hover:border-white/30 transition-colors text-sm font-medium"
                  >
                    <Link2 size={16} /> I have a code for another child
                  </button>
                </div>
              </>
            )}

            {view === 'add' && (
              <form onSubmit={handleAdd} className="flex flex-col gap-4">
                <input
                  value={addForm.firstName}
                  onChange={(e) => setAddForm((f) => ({ ...f, firstName: e.target.value }))}
                  placeholder="Child's first name"
                  className="w-full px-4 py-2.5 rounded-xl bg-white/[0.05] border border-white/10 text-paper
                             placeholder:text-paper/30 focus:outline-none focus:border-coral/50"
                />
                <div className="flex gap-2 flex-wrap">
                  {AVATAR_OPTIONS.map((a) => (
                    <button
                      type="button"
                      key={a}
                      onClick={() => setAddForm((f) => ({ ...f, avatar: a }))}
                      className={`rounded-full transition-all ${addForm.avatar === a ? 'ring-2 ring-coral' : 'opacity-60 hover:opacity-100'}`}
                    >
                      <Avatar avatar={a} size="sm" />
                    </button>
                  ))}
                </div>
                <input
                  value={addForm.pin}
                  onChange={(e) => setAddForm((f) => ({ ...f, pin: e.target.value.replace(/\D/g, '').slice(0, 4) }))}
                  placeholder="4-digit PIN"
                  inputMode="numeric"
                  className="w-full px-4 py-2.5 rounded-xl bg-white/[0.05] border border-white/10 text-paper
                             placeholder:text-paper/30 focus:outline-none focus:border-coral/50"
                />
                <div className="flex gap-2">
                  <button type="button" onClick={() => setView('list')} className="flex-1 px-4 py-2.5 rounded-xl text-paper/60 hover:text-paper text-sm font-medium">
                    Back
                  </button>
                  <button type="submit" disabled={busy} className="flex-1 px-4 py-2.5 rounded-xl bg-coral text-ink font-semibold text-sm disabled:opacity-50">
                    {busy ? 'Adding…' : 'Add child'}
                  </button>
                </div>
              </form>
            )}

            {view === 'link' && (
              <form onSubmit={handleLink} className="flex flex-col gap-4">
                <input
                  value={linkCode}
                  onChange={(e) => setLinkCode(e.target.value)}
                  placeholder="Player code (e.g. FOX4821)"
                  className="w-full px-4 py-2.5 rounded-xl bg-white/[0.05] border border-white/10 text-paper
                             placeholder:text-paper/30 focus:outline-none focus:border-coral/50 uppercase"
                />
                <div className="flex gap-2">
                  <button type="button" onClick={() => setView('list')} className="flex-1 px-4 py-2.5 rounded-xl text-paper/60 hover:text-paper text-sm font-medium">
                    Back
                  </button>
                  <button type="submit" disabled={busy} className="flex-1 px-4 py-2.5 rounded-xl bg-coral text-ink font-semibold text-sm disabled:opacity-50">
                    {busy ? 'Linking…' : 'Link child'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  )
}
