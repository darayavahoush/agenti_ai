import { useEffect } from 'react'

// Warns before the tab closes/reloads if isDirty is true. Browsers ignore
// any custom message text and show their own generic prompt -- the
// preventDefault + returnValue combo is what's actually required to
// trigger it (Chrome needs returnValue set, Firefox/Safari just need
// preventDefault, so both are set for cross-browser coverage).
export function useUnsavedChangesWarning(isDirty) {
  useEffect(() => {
    if (!isDirty) return

    const handler = (e) => {
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [isDirty])
}
