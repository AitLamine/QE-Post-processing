'use client'
import { useState, useEffect } from 'react'
import UploadWidget from './UploadWidget'
import PdosFileLabels from './PdosFileLabels'
import ManualPdosEntries from './ManualPdosEntries'

const SAMPLE_ENTRIES = [
  {
    species: 'Zn', orbital: 's', shell: '4',
    text: '# E (eV)   ldos(E)\n-10.000   0.0012\n-9.500    0.0034\n-9.000    0.0210\n' +
      '-8.500    0.0890\n-8.000    0.1520\n-7.500    0.0710\n-7.000    0.0180\n-6.500    0.0020',
  },
  {
    species: 'O', orbital: 'p', shell: '2',
    text: '# E (eV)   ldos(E)\n-10.000   0.0450\n-9.500    0.2100\n-9.000    0.5800\n' +
      '-8.500    0.9200\n-8.000    0.6100\n-7.500    0.2400\n-7.000    0.0600\n-6.500    0.0080',
  },
]
const SAMPLE_DOS_FOR_FERMI =
  '#  E (eV)   dos(E)     Int dos(E) EFermi =    5.938 eV\n' +
  '-10.000   0.0000   0.0000\n-5.000    1.2000   3.4000\n0.000     0.0500  10.0000'

// pDOS takes a variable number of pdos_atm files (one per orbital/atom), so it can't use fixed
// per-role FileSlots like the other modules -- there's no fixed set of roles to assign slots
// to. It keeps its own local upload/paste choice instead, scoped to just this module.
export default function PdosUploadSection({
  files, setFiles, pdosLabels, setPdosLabels, dosForFermi, setDosForFermi,
  manualPdosEntries, setManualPdosEntries, manualDosForFermiText, setManualDosForFermiText,
  sampleTrigger, t,
}) {
  const [mode, setMode] = useState('upload')

  useEffect(() => {
    if (!sampleTrigger) return
    setMode('manual')
    setManualPdosEntries(SAMPLE_ENTRIES.map((e) => ({ ...e })))
    setManualDosForFermiText(SAMPLE_DOS_FOR_FERMI)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sampleTrigger])

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
