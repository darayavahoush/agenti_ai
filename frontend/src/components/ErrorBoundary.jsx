import { Component } from 'react'

// Catches render/runtime errors anywhere below it in the tree and shows a
// friendly fallback instead of a white screen. React error boundaries must
// be class components -- there's no hook equivalent.
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error('Vaaksudhi crashed:', error, info)
  }

  handleReload = () => {
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
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
