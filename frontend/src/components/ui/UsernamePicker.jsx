import { useState, useEffect, useRef } from 'react'
import { AtSign, Check, X, Loader2, Shuffle } from 'lucide-react'
import { Input, Button } from './index'
import { usernameAPI } from '../../api/client'
import { validateUsernameFormat } from '../../utils/username'

// Shared @username input for kid / parent / therapist -- validates the
// format instantly client-side (utils/username.js, mirroring the backend's
// own rules), then debounces a live /check call against the database for
// the things only the server knows: the reserved-word list and whether the
// name is actually taken. Used both inside UsernameGate (first-login,
// can't be skipped) and each role's Settings page (editing an existing
// handle, cancelable).
//
// `role` selects which of usernameAPI's three endpoint sets to hit.
// `seedHint` (kid only, e.g. the chosen avatar) just flavours suggestions
// server-side -- see username_routes.py's seed_attr.
export default function UsernamePicker({ role, currentUsername = null, onSaved, onCancel }) {
  const [value, setValue] = useState(currentUsername || '')
  const [checking, setChecking] = useState(false)
  const [checkResult, setCheckResult] = useState(null) // { available, reason } | null
  const [suggestions, setSuggestions] = useState([])
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)
  const debounceRef = useRef(null)
  const api = usernameAPI[role]

  const { normalized, error: formatError } = validateUsernameFormat(value)
  const unchanged = currentUsername && normalized === currentUsername

  // Debounced live availability check -- skips the network call entirely
  // when the format is already invalid client-side, or when the value is
  // just the account's own current handle (server treats that as
  // available too, but there's no reason to round-trip for it).
  useEffect(() => {
    setCheckResult(null)
    if (formatError || unchanged) { setChecking(false); return }
    setChecking(true)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      try {
        const { data } = await api.check(normalized)
        setCheckResult(data)
      } catch {
        // Best-effort -- a failed live check just means no green/red
        // feedback yet; the real validation still happens on submit.
        setCheckResult(null)
      } finally {
        setChecking(false)
      }
    }, 400)
    return () => clearTimeout(debounceRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [normalized, formatError, unchanged])

  const loadSuggestions = async () => {
    setLoadingSuggestions(true)
    try {
      const { data } = await api.suggestions()
      setSuggestions(data.suggestions || [])
    } catch {
      setSuggestions([])
    } finally {
      setLoadingSuggestions(false)
    }
  }

  useEffect(() => { loadSuggestions() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const canSave = !formatError && !saving && (unchanged || checkResult?.available)

  const handleSave = async () => {
    if (!canSave) return
    if (unchanged) { onSaved?.(currentUsername); return }
    setSaving(true)
    setSaveError(null)
    try {
      const { data } = await api.set(normalized)
      onSaved?.(data.username)
    } catch (e) {
      // 409 (just got taken by someone else) or 422 (reserved word the
      // client-side check doesn't know about) -- either way, re-run the
      // check so the red/green state matches what the server just said.
      setSaveError(e.response?.data?.detail || 'Something went wrong — try again.')
      setCheckResult(null)
    } finally {
      setSaving(false)
    }
  }

  let statusIcon = null
  if (value && !formatError) {
    if (checking) statusIcon = <Loader2 size={16} className="animate-spin text-white/40" />
    else if (unchanged || checkResult?.available) statusIcon = <Check size={16} className="text-brand-green" />
    else if (checkResult && !checkResult.available) statusIcon = <X size={16} className="text-brand-coral" />
  }

  const liveError = formatError
    ? (value ? formatError : null)
    : (checkResult && !checkResult.available ? checkResult.reason : null)

  return (
    <div className="flex flex-col gap-3">
      <Input
        icon={AtSign}
        rightElement={statusIcon}
        value={value}
        onChange={(e) => { setValue(e.target.value); setSaveError(null) }}
        placeholder="sunny.otter"
        maxLength={20}
        error={liveError || saveError}
        autoFocus
      />

      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setValue(s)}
              className="px-3 py-1.5 rounded-full text-xs font-medium bg-white/[0.06] border border-white/10
                         text-white/70 hover:bg-white/10 hover:text-white transition-colors"
            >
              @{s}
            </button>
          ))}
          <button
            type="button"
            onClick={loadSuggestions}
            disabled={loadingSuggestions}
            title="More ideas"
            className="w-7 h-7 rounded-full bg-white/[0.06] border border-white/10 text-white/40
                       hover:text-white hover:bg-white/10 transition-colors flex items-center justify-center disabled:opacity-40"
          >
            <Shuffle size={12} className={loadingSuggestions ? 'animate-spin' : ''} />
          </button>
        </div>
      )}

      <div className="flex gap-3">
        <Button variant="primary" size="sm" disabled={!canSave} onClick={handleSave}>
          {saving ? <Loader2 size={14} className="animate-spin" /> : 'Save username'}
        </Button>
        {onCancel && (
          <Button variant="ghost" size="sm" onClick={onCancel} disabled={saving}>
            Cancel
          </Button>
        )}
      </div>
    </div>
  )
}
