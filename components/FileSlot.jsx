'use client'
import { useState } from 'react'
import UploadWidget from './UploadWidget'

// One file-role slot with its own independent upload/paste choice -- not a whole-form mode,
// a per-field one. "Upload" is the default (real calculation files are what the parser is
// built around); "Paste" is there for a student who'd rather not hand over this one
// particular file but can still type/paste the numbers it would have contained.
export default function FileSlot({ label, filename, placeholder, onFilesChange }) {
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
