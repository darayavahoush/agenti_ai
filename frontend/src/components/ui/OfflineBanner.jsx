import { useEffect, useState } from 'react'
import { WifiOff } from 'lucide-react'

// Shows a sticky bar whenever the browser reports no network connection,
// so failed requests read as "you're offline" instead of a generic error.
// navigator.onLine can false-positive on captive portals / flaky wifi, but
// it's still a strict improvement over no signal at all.
export default function OfflineBanner() {
  const [isOffline, setIsOffline] = useState(
    typeof navigator !== 'undefined' ? !navigator.onLine : false
  )

  useEffect(() => {
    const goOffline = () => setIsOffline(true)
    const goOnline = () => setIsOffline(false)
    window.addEventListener('offline', goOffline)
    window.addEventListener('online', goOnline)
    return () => {
      window.removeEventListener('offline', goOffline)
      window.removeEventListener('online', goOnline)
    }
  }, [])

  if (!isOffline) return null

  return (
    <div className="sticky top-0 z-50 flex items-center justify-center gap-3 px-4 py-2
                     bg-red-500/95 text-white text-sm font-semibold backdrop-blur-sm
                     shadow-[0_2px_12px_-4px_rgba(0,0,0,0.4)]">
      <WifiOff size={15} className="shrink-0" />
      <span>You're offline — some things may not work until you're back online.</span>
    </div>
  )
}
