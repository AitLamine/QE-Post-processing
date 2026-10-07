'use client'
import { useState } from 'react'
import UploadWidget from './UploadWidget'
import PdosFileLabels from './PdosFileLabels'
import ManualPdosEntries from './ManualPdosEntries'

// pDOS takes a variable number of pdos_atm files (one per orbital/atom), so it can't use fixed
// per-role FileSlots like the other modules -- there's no fixed set of roles to assign slots
// to. It keeps its own local upload/paste choice instead, scoped to just this module.
export default function PdosUploadSection({
  files, setFiles, pdosLabels, setPdosLabels, dosForFermi, setDosForFermi,
  manualPdosEntries, setManualPdosEntries, manualDosForFermiText, setManualDosForFermiText, t,
}) {
  const [mode, setMode] = useState('upload')

  return (
    <>
      <div className="input-mode-toggle">
        <label className={`mode-toggle-option${mode === 'upload' ? ' checked' : ''}`}>
          <input type="radio" name="pdosMode" checked={mode === 'upload'} onChange={() => setMode('upload')} />
          {t('modeUploadLabel')}
        </label>
        <label className={`mode-toggle-option${mode === 'manual' ? ' checked' : ''}`}>
          <input type="radio" name="pdosMode" checked={mode === 'manual'} onChange={() => setMode('manual')} />
          {t('modeManualLabel')}
        </label>
      </div>

      {mode === 'upload' ? (
        <>
          <UploadWidget files={files} onChange={setFiles} />
          <PdosFileLabels files={files} labels={pdosLabels} onChange={setPdosLabels} />
          <div style={{ marginTop: 16 }}>
            <UploadWidget
              label="dos.x output (optional — only used to auto-detect the VBM/Fermi energy)"
              files={dosForFermi}
              onChange={setDosForFermi}
            />
          </div>
        </>
      ) : (
        <div className="manual-entry">
          <p className="manual-help">{t('manualEntryIntro')}</p>
          <ManualPdosEntries entries={manualPdosEntries} onChange={setManualPdosEntries} />
          <div className="param-field" style={{ marginTop: 16 }}>
            <label>{t('manualDosForFermiLabel')}</label>
            <textarea
              className="manual-paste-textarea"
              rows={4}
              value={manualDosForFermiText}
              onChange={(e) => setManualDosForFermiText(e.target.value)}
              placeholder={'#  E (eV)   dos(E)     Int dos(E) EFermi =    5.938 eV\n...'}
            />
          </div>
        </div>
      )}
    </>
  )
}
