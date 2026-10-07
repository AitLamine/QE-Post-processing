'use client'
import { useState, useEffect } from 'react'
import UploadWidget from './UploadWidget'

// One file-role slot with its own independent upload/paste choice -- not a whole-form mode,
// a per-field one. "Upload" is the default (real calculation files are what the parser is
// built around); "Paste" is there for a student who'd rather not hand over this one
// particular file but can still type/paste the numbers it would have contained.
//
// `sampleText` + `fillTrigger`: when the page's "Try with sample data" action fires, the
// parent bumps `fillTrigger` for every slot at once; each slot reacts by switching itself to
// paste mode and filling in its own `sampleText` (the module's own placeholder content --
// real, validated example data, not placeholder lorem-ipsum). A no-op until the first bump.
export default function FileSlot({ label, filename, placeholder, sampleText, fillTrigger, onFilesChange }) {
  const [mode, setMode] = useState('upload')
  const [uploaded, setUploaded] = useState([])
  const [text, setText] = useState('')

  function report(nextMode, nextUploaded, nextText) {
    if (nextMode === 'upload') {
      onFilesChange(nextUploaded)
    } else {
      onFilesChange(nextText.trim() ? [new File([nextText], filename, { type: 'text/plain' })] : [])
    }
  }

  function handleModeChange(next) {
    setMode(next)
    report(next, uploaded, text)
  }

  function handleUploadChange(nextFiles) {
    setUploaded(nextFiles)
    if (mode === 'upload') report('upload', nextFiles, text)
  }

  function handleTextChange(e) {
    const value = e.target.value
    setText(value)
    if (mode === 'paste') report('paste', uploaded, value)
  }

  useEffect(() => {
    if (!fillTrigger) return
    const value = sampleText || ''
    setMode('paste')
    setText(value)
    report('paste', uploaded, value)
    // Only react to the trigger changing, not to every render -- intentionally narrow deps.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fillTrigger])

  return (
    <div className="param-field file-slot">
      <div className="file-slot-header">
        <label>{label}</label>
        <div className="input-mode-toggle file-slot-toggle">
          <label className={`mode-toggle-option${mode === 'upload' ? ' checked' : ''}`}>
            <input type="radio" checked={mode === 'upload'} onChange={() => handleModeChange('upload')} />
            Upload
          </label>
          <label className={`mode-toggle-option${mode === 'paste' ? ' checked' : ''}`}>
            <input type="radio" checked={mode === 'paste'} onChange={() => handleModeChange('paste')} />
            Paste instead
          </label>
        </div>
      </div>
      {mode === 'upload' ? (
        <UploadWidget files={uploaded} onChange={handleUploadChange} />
      ) : (
        <textarea
          className="manual-paste-textarea"
          rows={6}
          value={text}
          placeholder={placeholder}
          onChange={handleTextChange}
        />
      )}
    </div>
  )
}
