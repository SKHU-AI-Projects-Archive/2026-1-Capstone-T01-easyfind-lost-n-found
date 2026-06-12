import { createContext, useContext, useState } from 'react'
import translations from './i18n'

const LanguageContext = createContext()

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('lang') || 'en')

  const t = (key, ...args) => {
    const val = translations[lang]?.[key]
    if (typeof val === 'function') return val(...args)
    return val ?? key
  }

  const setLanguage = (newLang) => {
    setLang(newLang)
    localStorage.setItem('lang', newLang)
  }

  return (
    <LanguageContext.Provider value={{ lang, t, setLanguage }}>
      {children}
    </LanguageContext.Provider>
  )
}

export const useLanguage = () => useContext(LanguageContext)
