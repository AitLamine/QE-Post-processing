'use client'
import { useLang } from '@/lib/LangContext'

export default function JobStatusIndicator({ status }) {
  const { t } = useLang()
  const labels = {
    idle: t('jobIdle'),
    processing: t('jobProcessing'),
    done: t('jobDone'),
    failed: t('jobFailed'),
  }
  return (
    <div className={`job-status ${status}`}>
      <span className="dot" />
      <span>{labels[status]}</span>
    </div>
  )
}
