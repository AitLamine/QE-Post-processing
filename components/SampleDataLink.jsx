'use client'
import { useLang } from '@/lib/LangContext'

export default function SampleDataLink() {
  const { t } = useLang()
  return (
    <span className="sample-link" data-disabled="true" title={t('sampleLinkTitle')}>
      {t('sampleLinkText')}
    </span>
  )
}
