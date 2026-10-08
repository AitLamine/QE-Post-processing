'use client'
import Link from 'next/link'
import { useLang } from '@/lib/LangContext'

export default function Header({ theme, onToggleTheme }) {
  const { lang, setLang, t } = useLang()

  return (
    <header className="header">
      <Link href="/" className="header-title">
        <span className="header-dot" />
        <h1>QE Post-processing Lab</h1>
        <span className="header-dot" style={{ background: 'var(--accent2)' }} />
      </Link>
      <span className="header-beta-badge">{t('headerBetaBadge')}</span>
      <div className="header-controls">
      <button
        className="btn-action"
        onClick={() => setLang(lang === 'en' ? 'fr' : 'en')}
      >
        {t('langToggle')}
      </button>
      <button
        className="btn-action"
        onClick={onToggleTheme}
        title={theme === 'dark' ? t('themeToLight') : t('themeToDark')}
        aria-label={theme === 'dark' ? t('themeToLight') : t('themeToDark')}
      >
        {theme === 'dark' ? '☀️' : '🌙'}
      </button>
      </div>
    </header>
  )
}
