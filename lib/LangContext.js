'use client'
import { createContext, useContext } from 'react'
import { STRINGS } from './translations'

export const LangContext = createContext({ lang: 'en', setLang: () => {} })

export function useLang() {
  const { lang, setLang } = useContext(LangContext)
  const t = (key) => (STRINGS[lang] && STRINGS[lang][key]) || STRINGS.en[key] || key
  return { lang, setLang, t }
}
