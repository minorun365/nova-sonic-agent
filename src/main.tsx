import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Amplify } from 'aws-amplify'
import { I18n } from 'aws-amplify/utils'
import { translations } from '@aws-amplify/ui-react'
import './index.css'
import App from './App.tsx'

async function initializeApp() {
  I18n.putVocabularies(translations)
  I18n.setLanguage('ja')

  const outputs = await import('../amplify_outputs.json')
  Amplify.configure(outputs.default)

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

initializeApp()
