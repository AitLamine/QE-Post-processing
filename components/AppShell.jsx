'use client'
import { useEffect, useState } from 'react'
import Header from './Header'
import Footer from './Footer'
import { LangContext } from '@/lib/LangContext'

export default function AppShell({ children }) {
  const [theme, setThemeState] = useState('dark')
  const [lang, setLangState] = useState('en')

  // Restore-only: reads localStorage once on mount, never writes. Writing
  // happens exclusively in the toggle functions below, so there's no race
  // between a "restore" effect and a "persist" effect fighting over a stale
  // closure value during the same mount pass (that race is what silently
  // reset the language back to English on every reload).
  useEffect(() => {
    const storedTheme = window.localStorage.getItem('theme')
    if (storedTheme === 'light' || storedTheme === 'dark') setThemeState(storedTheme)
    const storedLang = window.localStorage.getItem('lang')
    if (storedLang === 'en' || storedLang === 'fr') setLangState(storedLang)
  }, [])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  useEffect(() => {
    document.documentElement.setAttribute('lang', lang)
  }, [lang])

  function setTheme(next) {
    setThemeState((prev) => {
      const value = typeof next === 'function' ? next(prev) : next
      window.localStorage.setItem('theme', value)
      return value
    })
  }

  function setLang(next) {
    setLangState((prev) => {
      const value = typeof next === 'function' ? next(prev) : next
      window.localStorage.setItem('lang', value)
      return value
    })
  }

  return (
    <LangContext.Provider value={{ lang, setLang }}>
      <div className="app-shell">
        <Header theme={theme} onToggleTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))} />
        <main className="main">{children}</main>
        <Footer />
      </div>
    </LangContext.Provider>
  )
}
