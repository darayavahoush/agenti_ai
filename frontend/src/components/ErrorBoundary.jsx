import { Component } from 'react'
import { LogOut, AlertTriangle } from 'lucide-react'
import { Button } from './ui'

// api/client.js's response interceptor handles a *clean* 401 (the backend
// rejecting the token) by clearing storage and hard-redirecting to login
// with ?session_expired=1 -- that path never reaches this boundary. What
// does land here is the messier case: the token is already gone from
// localStorage (cleared in another tab, expired mid-session, wiped by the
// browser) but a component in the tree still assumes a logged-in user is
// there and throws reading a property off something now null/undefined,
// before any request -- and therefore before that interceptor -- ever
// fires. Same "logged out" root cause, different code path, so it needs
// its own detection rather than falling through to the generic message.
function loginPathFor(userType) {
  if (userType === 'therapist') return '/therapist/login'
  if (userType === 'parent') return '/parent/login'
  return '/play' // kid landing -- mirrors ProtectedKid's own redirect target
}

// A tab left open across a deploy still holds the *old* chunk manifest --
// Vite's build output doesn't keep stale-hash files around, so the moment
// that tab lazy-loads a route/chunk it never fetched before the deploy, the
// dynamic import 404s and throws. Every major browser phrases this
// differently, so match all three rather than one exact string.
const STALE_CHUNK_PATTERN = /dynamically imported module|importing a module script failed/i

function isStaleChunkError(error) {
  return STALE_CHUNK_PATTERN.test(error?.message || '')
}

// Sessionstorage (not localStorage) so the guard is scoped to this tab and
// this load -- it resets the moment the tab is closed or a reload actually
// succeeds, but survives the reload itself so we don't loop forever if the
// stale chunk keeps 404ing (e.g. a CDN/edge cache still serving the old
// index.html, so every "fresh" load is actually still stale).
const STALE_CHUNK_RELOAD_KEY = 'bq_stale_chunk_reload_attempted'

// Catches render/runtime errors anywhere below it in the tree and shows a
// friendly fallback instead of a white screen. React error boundaries must
// be class components -- there's no hook equivalent.
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, loggedOut: false, staleChunk: false, staleChunkReloadFailed: false }
  }

  static getDerivedStateFromError(error) {
    // No token in storage at the moment we crash is a reliable signal this
    // was a dead session, not a real bug -- distinguish it here so the
    // fallback below can say something useful instead of "something went
    // wrong, try reloading" (which just reloads into the exact same crash).
    const loggedOut = !localStorage.getItem('bq_token')
    const staleChunk = isStaleChunkError(error)
    // If we already tried the auto-reload once this tab-session and landed
    // right back in the same error, reloading again won't help -- most
    // likely something (a CDN edge cache, a service worker) is still
    // serving the stale build even after a fresh navigation.
    const staleChunkReloadFailed = staleChunk && sessionStorage.getItem(STALE_CHUNK_RELOAD_KEY) === '1'
    return { hasError: true, loggedOut, staleChunk, staleChunkReloadFailed }
  }

  componentDidMount() {
    // Reaching a normal mount (this only runs on a mount that did NOT
    // immediately error, per React's error-boundary lifecycle) means
    // whatever's currently loaded is good. Clear the guard so a *later*,
    // unrelated stale-chunk incident in this same tab (e.g. the next
    // deploy, hours from now) still gets its own single auto-reload
    // instead of being treated as a repeat of one we already handled.
    sessionStorage.removeItem(STALE_CHUNK_RELOAD_KEY)
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error('Vaaksudhi crashed:', error, info)

    if (this.state.staleChunk && !this.state.staleChunkReloadFailed) {
      // One guarded, automatic reload -- the whole point is the user never
      // has to know this happened. Set the flag *before* reloading so if
      // the reload lands on this exact same error, getDerivedStateFromError
      // sees staleChunkReloadFailed=true next time and stops here instead
      // of reloading forever.
      sessionStorage.setItem(STALE_CHUNK_RELOAD_KEY, '1')
      window.location.reload()
    }
  }

  handleReload = () => {
    sessionStorage.removeItem(STALE_CHUNK_RELOAD_KEY)
    window.location.href = '/'
  }

  handleLogin = () => {
    const userType = localStorage.getItem('bq_user_type')
    // Clear out whatever's left so the login page starts from a clean
    // state rather than re-triggering the same crash on the way there.
    localStorage.removeItem('bq_token')
    localStorage.removeItem('bq_refresh_token')
    localStorage.removeItem('bq_user_type')
    localStorage.removeItem('bq_user_data')
    window.location.href = `${loginPathFor(userType)}?session_expired=1`
  }

  render() {
    if (this.state.hasError) {
      if (this.state.staleChunk && !this.state.staleChunkReloadFailed) {
        // componentDidCatch already fired window.location.reload() by the
        // time this renders -- this is just what's on screen for the brief
        // moment before the navigation actually completes, so it should
        // read as "hang on", not as an error the user needs to act on.
        return (
          <div className="min-h-screen flex items-center justify-center px-6">
            <div className="flex flex-col items-center gap-4 text-center max-w-sm">
              <div className="w-14 h-14 rounded-full bg-brand-teal/15 flex items-center justify-center mb-1 animate-pulse">
                <AlertTriangle className="w-6 h-6 text-brand-teal" />
              </div>
              <h1 className="font-display text-xl font-bold text-white">Updating…</h1>
              <p className="text-white/50 text-sm">
                This page was open across an app update. One moment while it refreshes.
              </p>
            </div>
          </div>
        )
      }

      if (this.state.staleChunkReloadFailed) {
        return (
          <div className="min-h-screen flex items-center justify-center px-6">
            <div className="flex flex-col items-center gap-4 text-center max-w-sm">
              <div className="w-14 h-14 rounded-full bg-brand-coral/15 flex items-center justify-center mb-1">
                <AlertTriangle className="w-6 h-6 text-brand-coral" />
              </div>
              <h1 className="font-display text-xl font-bold text-white">Still on an old version</h1>
              <p className="text-white/50 text-sm">
                An automatic refresh didn't pick up the latest update. Please close and
                reopen this tab, or hard-refresh (Cmd/Ctrl+Shift+R).
              </p>
              <Button variant="ghost" size="sm" className="mt-2" onClick={this.handleReload}>
                Try again
              </Button>
            </div>
          </div>
        )
      }

      if (this.state.loggedOut) {
        return (
          <div className="min-h-screen flex items-center justify-center px-6">
            <div className="flex flex-col items-center gap-4 text-center max-w-sm">
              <div className="w-14 h-14 rounded-full bg-brand-amber/15 flex items-center justify-center mb-1">
                <LogOut className="w-6 h-6 text-brand-amber" />
              </div>
              <h1 className="font-display text-xl font-bold text-white">You've been logged out</h1>
              <p className="text-white/50 text-sm">
                Your session ended, so this page couldn't load. Log back in to pick up
                where you left off — reloading won't fix this one.
              </p>
              <Button variant="primary" size="sm" className="mt-2" onClick={this.handleLogin}>
                Log in
              </Button>
            </div>
          </div>
        )
      }

      return (
        <div className="min-h-screen flex items-center justify-center px-6">
          <div className="flex flex-col items-center gap-4 text-center max-w-sm">
            <div className="w-14 h-14 rounded-full bg-brand-coral/15 flex items-center justify-center mb-1">
              <AlertTriangle className="w-6 h-6 text-brand-coral" />
            </div>
            <h1 className="font-display text-xl font-bold text-white">Something went wrong</h1>
            <p className="text-white/50 text-sm">
              This page hit an unexpected error. Reloading usually fixes it.
            </p>
            <Button variant="ghost" size="sm" className="mt-2" onClick={this.handleReload}>
              Back to home
            </Button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
