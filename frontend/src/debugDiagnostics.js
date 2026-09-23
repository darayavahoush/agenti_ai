// TEMP DIAGNOSTIC (2026-09-22) -- tracking the "Launch Assessment/Live
// Therapy bounces to therapist login" bug. Remove this whole file (and its
// one-line import in main.jsx) once the actual cause is confirmed.
//
// The previous capture attempts kept coming back empty: a plain `window`
// property doesn't survive a hard `window.location.href` reload, and the
// hard-logout branch client.js already instruments only covers ONE of the
// ways a reload or redirect can happen. This installs unconditionally on
// every page load (not just when someone remembers to paste a snippet
// first) and writes everything to localStorage, which *does* survive a
// full reload, so whatever happened is still there to read afterward.
//
// Three things get logged, each as a small ring buffer (last 10 entries)
// under its own key:
//   bq_debug_routes  -- every SPA route change (history.pushState/
//                        replaceState), so we can see whether the app
//                        ever soft-navigated to /therapist/login before
//                        any reload, or went straight to a reload with no
//                        SPA nav in between.
//   bq_debug_errors  -- every uncaught error / unhandled promise
//                        rejection, same info ErrorBoundary already logs
//                        to the console, just persisted this time.
//   bq_debug_unload  -- the exact pathname/href at the moment ANY unload
//                        starts (reload, hard redirect, or navigating
//                        away), which is the one signal that tells us a
//                        real reload happened vs. a same-page SPA change.

export function pushRingBuffer(key, entry, max = 10) {
  try {
    const raw = localStorage.getItem(key)
    const list = raw ? JSON.parse(raw) : []
    list.push({ ...entry, at: new Date().toISOString() })
    while (list.length > max) list.shift()
    localStorage.setItem(key, JSON.stringify(list))
  } catch {
    // best-effort -- a full storage quota or corrupt existing value
    // shouldn't ever be the thing that breaks the app
  }
}

for (const fnName of ['pushState', 'replaceState']) {
  const original = history[fnName]
  history[fnName] = function (...args) {
    const result = original.apply(this, args)
    pushRingBuffer('bq_debug_routes', {
      via: fnName,
      to: window.location.pathname + window.location.search,
    })
    return result
  }
}

window.addEventListener('error', (e) => {
  pushRingBuffer('bq_debug_errors', {
    kind: 'error',
    message: e.error?.stack || e.message,
    pathname: window.location.pathname,
  })
})

window.addEventListener('unhandledrejection', (e) => {
  pushRingBuffer('bq_debug_errors', {
    kind: 'unhandledrejection',
    message: e.reason?.stack || String(e.reason),
    pathname: window.location.pathname,
  })
})

window.addEventListener('beforeunload', () => {
  pushRingBuffer('bq_debug_unload', {
    pathname: window.location.pathname,
    href: window.location.href,
  })
})
