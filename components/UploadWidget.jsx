'use client'
import { useRef, useState } from 'react'
import { useLang } from '@/lib/LangContext'

const MAX_TOTAL_BYTES = 200 * 1024 * 1024 // 200 MB per upload slot, client-side guard only

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function UploadWidget({ label, checklist, files, onChange }) {
  const { t } = useLang()
  const inputRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState('')

  function addFiles(fileList) {
    const incoming = Array.from(fileList)
    const combined = [...files, ...incoming]
    const total = combined.reduce((sum, f) => sum + f.size, 0)
    if (total > MAX_TOTAL_BYTES) {
      setError(t('sizeLimitError').replace('{limit}', formatBytes(MAX_TOTAL_BYTES)))
      return
    }
    setError('')
    onChange(combined)
  }

  function removeFile(index) {
    onChange(files.filter((_, i) => i !== index))
  }

  return (
    <div>
      {label && <div className="param-field"><label>{label}</label></div>}
      <div
        className={`upload-dropzone${dragOver ? ' drag-over' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          addFiles(e.dataTransfer.files)
        }}
      >
        {t('dropzoneText')}
        <input
          ref={inputRef}
          type="file"
          multiple
          onChange={(e) => { addFiles(e.target.files); e.target.value = '' }}
        />
      </div>
      {checklist?.length > 0 && (
        <ul className="file-checklist">
          {checklist.map((item) => <li key={item}>{item}</li>)}
        </ul>
      )}
      {error && <div className="error-message">{error}</div>}
      {files.length > 0 && (
        <ul className="selected-files">
          {files.map((file, i) => (
            <li key={`${file.name}-${i}`}>
              <span>{file.name}</span>
              <span>
                <span className="file-size">{formatBytes(file.size)}</span>{' '}
                <button className="btn-action" style={{ padding: '2px 8px' }} onClick={() => removeFile(i)}>
                  {t('removeButton')}
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
