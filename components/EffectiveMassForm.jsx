'use client'
import { useState } from 'react'
import UploadWidget from './UploadWidget'
import JobStatusIndicator from './JobStatusIndicator'
import { useLang } from '@/lib/LangContext'

const AXIS_LABELS = { x: 'X-direction', y: 'Y-direction', z: 'Z-direction' }

// Dual-mode file slot: "upload" renders the normal UploadWidget unchanged; "manual" renders a
// textarea instead, so a student can paste the raw file content rather than upload their real
// QE calculation files. Either branch calls the same `onChange(files)` the caller already uses.
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

// Processes exactly one k-direction per submission (not 1-3 batched into one request): a
// student wanting more than one direction runs this module once per direction. Batching
// multiple directions into one request was the single biggest risk of hitting a serverless
// function timeout in this app, since each direction chains 6+ subprocess calls on its own.
//
// The real backend (api/effective-mass.py) expects a richer multi-file contract than the
// generic flat-upload TaskPage flow can express, so this module gets its own form.
export default function EffectiveMassForm({ module }) {
  const { t } = useLang()
  const [inputMode, setInputMode] = useState('upload')
  const [detectionMode, setDetectionMode] = useState('auto')
  const [directionAxis, setDirectionAxis] = useState('x')
  const [customLabel, setCustomLabel] = useState('')
  const [latticeConstant, setLatticeConstant] = useState('')
  const [vbmIndex, setVbmIndex] = useState('')
  const [datgnu, setDatgnu] = useState([])
  const [scfBandsIn, setScfBandsIn] = useState([])
  const [scfBandsOut, setScfBandsOut] = useState([])
  const [bandsCalcIn, setBandsCalcIn] = useState([])
  const [bandsCalcOut, setBandsCalcOut] = useState([])
  const [bandFile, setBandFile] = useState([])
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

  const directionLabel = directionAxis === 'custom' ? customLabel.trim() : AXIS_LABELS[directionAxis]

  const canSubmit =
    jobStatus !== 'processing' &&
    directionLabel &&
    (detectionMode === 'auto'
      ? [datgnu, scfBandsIn, scfBandsOut, bandsCalcIn, bandsCalcOut].every((f) => f.length > 0)
      : bandFile.length > 0 && latticeConstant !== '' && vbmIndex !== '')

  async function handleSubmit() {
    setError('')
    setJobStatus('processing')
    try {
      const formData = new FormData()
      formData.append('moduleId', module.id)
      formData.append('moduleTitle', module.title)

      const parameters = {
        detectionMode,
        directionLabel,
        nBandsBelowVbm, nBandsAboveCbm, pointsAroundExtremum,
        materialLabel,
        figureFormat,
        xRange, yRange,
      }
      if (detectionMode === 'manual') {
        parameters.latticeConstant = latticeConstant
        parameters.vbmIndex = vbmIndex
      }
      formData.append('parameters', JSON.stringify(parameters))

      if (detectionMode === 'auto') {
        if (datgnu[0]) formData.append('datgnu', datgnu[0])
        if (scfBandsIn[0]) formData.append('scfBandsIn', scfBandsIn[0])
        if (scfBandsOut[0]) formData.append('scfBandsOut', scfBandsOut[0])
        if (bandsCalcIn[0]) formData.append('bandsCalcIn', bandsCalcIn[0])
        if (bandsCalcOut[0]) formData.append('bandsCalcOut', bandsCalcOut[0])
      } else {
        if (bandFile[0]) formData.append('bandFile', bandFile[0])
      }
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
        <h2>1. This direction</h2>
        <p className="manual-help">
          One k-direction per run. Want more than one? Submit this form again for the next
          direction once this one's done — each run downloads its own zip with that
          direction's mass value and fit plot.
        </p>
        <div className="param-field">
          <label>Detection mode</label>
          <select value={detectionMode} onChange={(e) => setDetectionMode(e.target.value)}>
            <option value="auto">Auto (raw QE files: .dat.gnu + scf-bands + Bands-Calculation .in/.out)</option>
            <option value="manual">Manual (one already-extracted band-data file + typed lattice constant/VBM index)</option>
          </select>
        </div>
        <div className="param-field">
          <label>Direction</label>
          <select value={directionAxis} onChange={(e) => setDirectionAxis(e.target.value)}>
            <option value="x">X-direction</option>
            <option value="y">Y-direction</option>
            <option value="z">Z-direction</option>
            <option value="custom">Custom label…</option>
          </select>
        </div>
        {directionAxis === 'custom' && (
          <div className="param-field">
            <label>Custom direction label</label>
            <input type="text" value={customLabel} placeholder="e.g. Gamma-to-A"
                   onChange={(e) => setCustomLabel(e.target.value)} />
          </div>
        )}

        {detectionMode === 'auto' ? (
          <>
            <DualFileSlot mode={inputMode} label="Band-structure .dat.gnu file" files={datgnu}
                          filename="Bands.dat.gnu"
                          placeholder={'0.000000  -5.432100\n0.012345  -5.431000\n...\n\n0.000000  -1.234000\n...'}
                          onChange={setDatgnu} />
            <div style={{ marginTop: 12 }}>
              <DualFileSlot mode={inputMode} label="scf-bands calculation .in file" files={scfBandsIn}
                            filename="scf-bands-Calculation.in"
                            placeholder={'&CONTROL\n  calculation = \'scf\'\n...\nibrav = 4\ncelldm(1) = 6.1234\ncelldm(3) = 1.602\n...'}
                            onChange={setScfBandsIn} />
            </div>
            <div style={{ marginTop: 12 }}>
              <DualFileSlot mode={inputMode} label="scf-bands calculation .out file" files={scfBandsOut}
                            filename="scf-bands-Calculation.out"
                            placeholder={'Program PWSCF ...\n...\nnumber of electrons       =    36.00\n...'}
                            onChange={setScfBandsOut} />
            </div>
            <div style={{ marginTop: 12 }}>
              <DualFileSlot mode={inputMode} label="Bands-Calculation .in file" files={bandsCalcIn}
                            filename="Bands-Calculation.in"
                            placeholder={'&CONTROL\n  calculation = \'bands\'\n...\nK_POINTS crystal_b\n5\n0.0 0.0 0.0 20 !G\n...'}
                            onChange={setBandsCalcIn} />
            </div>
            <div style={{ marginTop: 12 }}>
              <DualFileSlot mode={inputMode} label="Bands-Calculation .out file" files={bandsCalcOut}
                            filename="Bands-Calculation.out"
                            placeholder={'Program PWSCF ...\n...\nnumber of electrons       =    36.00\n...'}
                            onChange={setBandsCalcOut} />
            </div>
          </>
        ) : (
          <>
            <DualFileSlot mode={inputMode} label="Band-structure data file" files={bandFile}
                          filename="band-data.dat.gnu"
                          placeholder={'0.000000  -5.432100\n0.012345  -5.431000\n...'}
                          onChange={setBandFile} />
            <div className="param-field" style={{ marginTop: 12 }}>
              <label>Lattice constant a (Angstrom)</label>
              <input type="text" value={latticeConstant} onChange={(e) => setLatticeConstant(e.target.value)} />
            </div>
            <div className="param-field">
              <label>VBM band index</label>
              <input type="number" value={vbmIndex} onChange={(e) => setVbmIndex(e.target.value)} />
            </div>
          </>
        )}
      </div>

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
          <p className="manual-help" style={{ marginTop: 4 }}>
            Check the fit plot in the downloaded zip after a first run — if the fitted parabola
            doesn't track the data well near the extremum, adjust this (and re-run) before
            trusting the mass value.
          </p>
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
        <p className="manual-help">
          The mass value (table/CSV) is the main result most students need. The fit plot is
          included as a diagnostic — use it to check whether your fitting parameters above were
          a good choice before trusting the number.
        </p>
        <button className="btn-primary" disabled={!canSubmit} onClick={handleSubmit}>
          Process & download zip
        </button>
        <JobStatusIndicator status={jobStatus} />
        {error && <div className="error-message">{error}</div>}
      </div>
    </div>
  )
}
