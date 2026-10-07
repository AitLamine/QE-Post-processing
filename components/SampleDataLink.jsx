'use client'
import { useLang } from '@/lib/LangContext'

export default function SampleDataLink({ onClick }) {
  const { t } = useLang()
  if (!onClick) return null
  return (
    <button type="button" className="sample-link" title={t('sampleLinkTitle')} onClick={onClick}>
      {t('sampleLinkText')}
    </button>
  )
}
