import { Component } from 'react'

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

// Catches render/runtime errors anywhere below it in the tree and shows a
// friendly fallback instead of a white screen. React error boundaries must
// be class components -- there's no hook equivalent.
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, loggedOut: false }
  }

  static getDerivedStateFromError() {
    // No token in storage at the moment we crash is a reliable signal this
    // was a dead session, not a real bug -- distinguish it here so the
    // fallback below can say something useful instead of "something went
    // wrong, try reloading" (which just reloads into the exact same crash).
    const loggedOut = !localStorage.getItem('bq_token')
    return { hasError: true, loggedOut }
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error('Vaaksudhi crashed:', error, info)
  }

  handleReload = () => {
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
      if (this.state.loggedOut) {
        return (
          <div className="min-h-screen flex items-center justify-center px-6">
            <div className="flex flex-col items-center gap-4 text-center max-w-sm">
              <h1 className="font-display text-xl font-bold text-paper">You've been logged out</h1>
              <p className="text-white/50 text-sm">
                Your session ended, so this page couldn't load. Log back in to pick up
                where you left off -- reloading won't fix this one.
              </p>
              <button
                onClick={this.handleLogin}
                className="mt-2 px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-paper text-sm font-medium transition"
              >
                Log in
              </button>
            </div>
          </div>
        )
      }

      return (
        <div className="min-h-screen flex items-center justify-center px-6">
          <div className="flex flex-col items-center gap-4 text-center max-w-sm">
            <h1 className="font-display text-xl font-bold text-paper">Something went wrong</h1>
            <p className="text-white/50 text-sm">
              This page hit an unexpected error. Reloading usually fixes it.
            </p>
            <button
              onClick={this.handleReload}
              className="mt-2 px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-paper text-sm font-medium transition"
            >
              Back to home
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
