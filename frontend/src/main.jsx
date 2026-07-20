import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './i18n';
import App from './App.jsx'
import { normalizeLocalOAuthOrigin } from './utils/oauthConfig'

if (!normalizeLocalOAuthOrigin()) {
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}
