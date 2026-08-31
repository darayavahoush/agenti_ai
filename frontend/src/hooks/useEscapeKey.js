import { useEffect } from 'react'

// Calls onEscape when the Escape key is pressed while mounted. Pass the
// modal's own close handler (or a confirm-then-close wrapper) so Escape
// behaves the same as clicking its close button.
export function useEscapeKey(onEscape) {
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') onEscape()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onEscape])
}
