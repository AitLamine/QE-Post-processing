'use client'
import { useState } from 'react'
import UploadWidget from './UploadWidget'
import JobStatusIndicator from './JobStatusIndicator'
import { useLang } from '@/lib/LangContext'

const DEFAULT_DIRECTION_LABELS = ['First-Direction', 'Second-Direction', 'Third-Direction']

// Dual-mode file slot: "upload" renders the normal UploadWidget unchanged; "manual" renders a
// textarea instead, so a student can paste the raw file content rather than upload their real
// QE calculation files. Either branch calls the same `onChange(files)` the caller already uses,
// so nothing downstream (directionReady/handleSubmit) needs to know which mode produced the file.
function DualFileSlot({ mode, label, filename, placeholder, files, onChange }) {
  const [text, setText] = useState('')
  if (mode === 'upload') {
    return <UploadWidget label={label} files={files} onChange={onChange} />
  }
  return (
    <div className="param-field">
      <label>{label} — paste its content</label>
      <textarea
        className="manual-paste-textarea"
        rows={6}
        value={text}
        placeholder={placeholder}
        onChange={(e) => {
          const value = e.target.value
          setText(value)
          onChange(value.trim() ? [new File([value], filename, { type: 'text/plain' })] : [])
        }}
      />
    </div>
  )
}

function emptyDirection(index) {
  return {
    label: DEFAULT_DIRECTION_LABELS[index] || `Direction-${index + 1}`,
    latticeConstant: '',
    vbmIndex: '',
    datgnu: [], scfBandsIn: [], scfBandsOut: [], bandsCalcIn: [], bandsCalcOut: [],
    bandFile: [],
  }
}

// The real backend (api/effective-mass.py) expects a richer, per-direction multi-file contract
// than the generic flat-upload TaskPage flow can express, so this module gets its own form.
export default function EffectiveMassForm({ module }) {
  const { t } = useLang()
  const [inputMode, setInputMode] = useState('upload')
  const [detectionMode, setDetectionMode] = useState('auto')
  const [numDirections, setNumDirections] = useState(1)
  const [directions, setDirections] = useState([emptyDirection(0)])
  const [nBandsBelowVbm, setNBandsBelowVbm] = useState(3)
  const [nBandsAboveCbm, setNBandsAboveCbm] = useState(3)
  const [pointsAroundExtremum, setPointsAroundExtremum] = useState(10)
  const [materialLabel, setMaterialLabel] = useState('')
  const [figureFormat, setFigureFormat] = useState('PNG')
  const [xRange, setXRange] = useState('')
  const [yRange, setYRange] = useState('')
  const [templateFile, setTemplateFile] = useState([])
  const [jobStatus, setJobStatus] = useState('idle')
  const [error, setError] = useState('')

  function setNumDirectionsClamped(n) {
    const count = Math.max(1, Math.min(3, Number(n) || 1))
    setNumDirections(count)
    setDirections((prev) => {
      const next = [...prev]
      while (next.length < count) next.push(emptyDirection(next.length))
      return next.slice(0, count)
    })
  }

  function updateDirection(index, patch) {
    setDirections((prev) => prev.map((d, i) => (i === index ? { ...d, ...patch } : d)))
  }

  function directionReady(d) {
    if (detectionMode === 'auto') {
      return [d.datgnu, d.scfBandsIn, d.scfBandsOut, d.bandsCalcIn, d.bandsCalcOut].every((f) => f.length > 0)
    }
    return d.bandFile.length > 0 && d.latticeConstant !== '' && d.vbmIndex !== ''
  }

  const canSubmit = jobStatus !== 'processing' && directions.every(directionReady)

  async function handleSubmit() {
    setError('')
    setJobStatus('processing')
    try {
      const formData = new FormData()
      formData.append('moduleId', module.id)
      formData.append('moduleTitle', module.title)

      const parameters = {
        detectionMode,
        numDirections,
        nBandsBelowVbm, nBandsAboveCbm, pointsAroundExtremum,
        materialLabel,
        figureFormat,
        xRange, yRange,
      }
      directions.forEach((d, i) => {
        const n = i + 1
        parameters[`direction${n}Label`] = d.label
        if (detectionMode === 'manual') {
          parameters[`direction${n}LatticeConstant`] = d.latticeConstant
          parameters[`direction${n}VbmIndex`] = d.vbmIndex
        }
      })
      formData.append('parameters', JSON.stringify(parameters))

      directions.forEach((d, i) => {
        const n = i + 1
        if (detectionMode === 'auto') {
          if (d.datgnu[0]) formData.append(`direction${n}_datgnu`, d.datgnu[0])
          if (d.scfBandsIn[0]) formData.append(`direction${n}_scfBandsIn`, d.scfBandsIn[0])
          if (d.scfBandsOut[0]) formData.append(`direction${n}_scfBandsOut`, d.scfBandsOut[0])
          if (d.bandsCalcIn[0]) formData.append(`direction${n}_bandsCalcIn`, d.bandsCalcIn[0])
          if (d.bandsCalcOut[0]) formData.append(`direction${n}_bandsCalcOut`, d.bandsCalcOut[0])
        } else {
          if (d.bandFile[0]) formData.append(`direction${n}_bandFile`, d.bandFile[0])
        }
      })
      if (templateFile[0]) formData.append('templateFile', templateFile[0])

      const res = await fetch(module.apiEndpoint, { method: 'POST', body: formData })
      if (!res.ok) {
        let message = `Server returned ${res.status}`
        try {
          const body = await res.json()
          if (body?.error) message = body.error
        } catch {}
        throw new Error(message)
      }

      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${module.title.replace(/[^a-z0-9]+/gi, '-')}-Results.zip`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      setJobStatus('done')
    } catch (err) {
      setError(err.message || 'Something went wrong building the result zip. Please try again.')
      setJobStatus('failed')
    }
  }

  return (
    <div>
      <div className="section-block">
        <h2>0. Input source</h2>
        <p className="manual-help">{t('manualEntryIntro')}</p>
        <div className="input-mode-toggle">
          <label className={`mode-toggle-option${inputMode === 'upload' ? ' checked' : ''}`}>
            <input type="radio" name="emInputMode" checked={inputMode === 'upload'} onChange={() => setInputMode('upload')} />
            {t('modeUploadLabel')}
          </label>
          <label className={`mode-toggle-option${inputMode === 'manual' ? ' checked' : ''}`}>
            <input type="radio" name="emInputMode" checked={inputMode === 'manual'} onChange={() => setInputMode('manual')} />
            {t('modeManualLabel')}
          </label>
        </div>
      </div>

      <div className="section-block">
        <h2>1. Detection mode</h2>
        <div className="param-field">
          <label>Mode</label>
          <select value={detectionMode} onChange={(e) => setDetectionMode(e.target.value)}>
            <option value="auto">Auto (raw QE files: .dat.gnu + scf-bands + Bands-Calculation .in/.out)</option>
            <option value="manual">Manual (one already-extracted band-data file + typed lattice constant/VBM index)</option>
          </select>
        </div>
        <div className="param-field">
          <label>Number of k-directions (1-3)</label>
          <input type="number" min={1} max={3} value={numDirections}
                 onChange={(e) => setNumDirectionsClamped(e.target.value)} />
        </div>
      </div>

      {directions.map((d, i) => {
        const n = i + 1
        return (
        <div className="section-block" key={i}>
          <h2>Direction {i + 1}</h2>
          <div className="param-field">
            <label>Label</label>
            <input type="text" value={d.label} onChange={(e) => updateDirection(i, { label: e.target.value })} />
          </div>

          {detectionMode === 'auto' ? (
            <>
              <DualFileSlot mode={inputMode} label="Band-structure .dat.gnu file" files={d.datgnu}
                            filename={`Direction-${n}-Bands.dat.gnu`}
                            placeholder={'0.000000  -5.432100\n0.012345  -5.431000\n...\n\n0.000000  -1.234000\n...'}
                            onChange={(files) => updateDirection(i, { datgnu: files.slice(-1) })} />
              <div style={{ marginTop: 12 }}>
                <DualFileSlot mode={inputMode} label="scf-bands calculation .in file" files={d.scfBandsIn}
                              filename={`Direction-${n}-scf-bands-Calculation.in`}
                              placeholder={'&CONTROL\n  calculation = \'scf\'\n...\nibrav = 4\ncelldm(1) = 6.1234\ncelldm(3) = 1.602\n...'}
                              onChange={(files) => updateDirection(i, { scfBandsIn: files.slice(-1) })} />
              </div>
              <div style={{ marginTop: 12 }}>
                <DualFileSlot mode={inputMode} label="scf-bands calculation .out file" files={d.scfBandsOut}
                              filename={`Direction-${n}-scf-bands-Calculation.out`}
                              placeholder={'Program PWSCF ...\n...\nnumber of electrons       =    36.00\n...'}
                              onChange={(files) => updateDirection(i, { scfBandsOut: files.slice(-1) })} />
              </div>
              <div style={{ marginTop: 12 }}>
                <DualFileSlot mode={inputMode} label="Bands-Calculation .in file" files={d.bandsCalcIn}
                              filename={`Direction-${n}-Bands-Calculation.in`}
                              placeholder={'&CONTROL\n  calculation = \'bands\'\n...\nK_POINTS crystal_b\n5\n0.0 0.0 0.0 20 !G\n...'}
                              onChange={(files) => updateDirection(i, { bandsCalcIn: files.slice(-1) })} />
              </div>
              <div style={{ marginTop: 12 }}>
                <DualFileSlot mode={inputMode} label="Bands-Calculation .out file" files={d.bandsCalcOut}
                              filename={`Direction-${n}-Bands-Calculation.out`}
                              placeholder={'Program PWSCF ...\n...\nnumber of electrons       =    36.00\n...'}
                              onChange={(files) => updateDirection(i, { bandsCalcOut: files.slice(-1) })} />
              </div>
            </>
          ) : (
            <>
              <DualFileSlot mode={inputMode} label="Band-structure data file" files={d.bandFile}
                            filename={`Direction-${n}-band-data.dat.gnu`}
                            placeholder={'0.000000  -5.432100\n0.012345  -5.431000\n...'}
                            onChange={(files) => updateDirection(i, { bandFile: files.slice(-1) })} />
              <div className="param-field" style={{ marginTop: 12 }}>
                <label>Lattice constant a (Angstrom)</label>
                <input type="text" value={d.latticeConstant}
                       onChange={(e) => updateDirection(i, { latticeConstant: e.target.value })} />
              </div>
              <div className="param-field">
                <label>VBM band index</label>
                <input type="number" value={d.vbmIndex}
                       onChange={(e) => updateDirection(i, { vbmIndex: e.target.value })} />
              </div>
            </>
          )}
        </div>
        )
      })}

      <div className="section-block">
        <h2>2. Shared parameters</h2>
        <div className="param-field">
          <label>Bands below VBM to fit</label>
          <input type="number" value={nBandsBelowVbm} onChange={(e) => setNBandsBelowVbm(e.target.value)} />
        </div>
        <div className="param-field">
          <label>Bands above CBM to fit</label>
          <input type="number" value={nBandsAboveCbm} onChange={(e) => setNBandsAboveCbm(e.target.value)} />
        </div>
        <div className="param-field">
          <label>Points around extremum</label>
          <input type="number" value={pointsAroundExtremum} onChange={(e) => setPointsAroundExtremum(e.target.value)} />
        </div>
        <div className="param-field">
          <label>Material label (optional, for the report)</label>
          <input type="text" value={materialLabel} onChange={(e) => setMaterialLabel(e.target.value)} />
        </div>
        <div className="param-field">
          <label>Figure format</label>
          <select value={figureFormat} onChange={(e) => setFigureFormat(e.target.value)}>
            <option value="PNG">PNG</option>
            <option value="LaTeX (pgfplots)">LaTeX (pgfplots)</option>
            <option value="Both">Both</option>
          </select>
        </div>
        <div className="param-field">
          <label>X-axis range (optional — auto if left blank)</label>
          <input type="text" value={xRange} onChange={(e) => setXRange(e.target.value)} />
        </div>
        <div className="param-field">
          <label>Y-axis range (optional — auto if left blank)</label>
          <input type="text" value={yRange} onChange={(e) => setYRange(e.target.value)} />
        </div>
        <UploadWidget label="Custom LaTeX template (optional, .tex)" files={templateFile}
                      onChange={(files) => setTemplateFile(files.slice(-1))} />
      </div>

      <div className="section-block">
        <h2>3. Process & download</h2>
        <button className="btn-primary" disabled={!canSubmit} onClick={handleSubmit}>
          Process & download zip
        </button>
        <JobStatusIndicator status={jobStatus} />
        {error && <div className="error-message">{error}</div>}
      </div>
    </div>
  )
}
