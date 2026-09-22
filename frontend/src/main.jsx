import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './debugDiagnostics.js' // TEMP -- see file header, remove once the Launch bounce is found
import App from './App.jsx'
import { ErrorBoundary } from './components/ErrorBoundary.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
