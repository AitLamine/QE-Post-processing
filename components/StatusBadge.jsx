'use client'
import { STATUS_LABELS } from '@/lib/modules'
import { STATUS_LABELS_FR } from '@/lib/translations'
import { useLang } from '@/lib/LangContext'

export default function StatusBadge({ status }) {
  const { lang } = useLang()
  const label = (lang === 'fr' && STATUS_LABELS_FR[status]) || STATUS_LABELS[status] || status
  return <span className={`status-badge ${status}`}>{label}</span>
}
