'use client'
import { useState } from 'react'
import UploadWidget from './UploadWidget'
import FileSlot from './FileSlot'
import JobStatusIndicator from './JobStatusIndicator'
import { useLang } from '@/lib/LangContext'

const AXIS_LABELS = { x: 'X-direction', y: 'Y-direction', z: 'Z-direction' }
const BOHR_TO_ANGSTROM = 0.529177210903

// Processes exactly one k-direction per submission (not 1-3 batched into one request): a
// student wanting more than one direction runs this module once per direction. Batching
// multiple directions into one request was the single biggest risk of hitting a serverless
// function timeout in this app, since each direction chains 6+ subprocess calls on its own.
//
// Only ever takes typed lattice constant + VBM band index (never raw QE .in/.out files,
// upload or paste): those files carry the full crystal structure (ibrav/celldm/atomic
// positions), which is exactly the kind of data the per-field privacy model elsewhere in this
// app is built to avoid asking for. The "derive instead" helpers below do the same
// Bohr->Angstrom / nelec->band-index arithmetic the old file-based auto mode did, from typed
// numbers instead of uploaded structure files.
//
// The real backend (api/effective-mass.py) expects a richer multi-file contract than the
// generic flat-upload TaskPage flow can express, so this module gets its own form.
export default function EffectiveMassForm({ module }) {
  const { t } = useLang()
  const [directionAxis, setDirectionAxis] = useState('x')
  const [customLabel, setCustomLabel] = useState('')
  const [bandFile, setBandFile] = useState([])
  const [latticeConstant, setLatticeConstant] = useState('')
  const [showCelldmHelper, setShowCelldmHelper] = useState(false)
  const [celldm1Bohr, setCelldm1Bohr] = useState('')
  const [vbmIndex, setVbmIndex] = useState('')
  const [showNelecHelper, setShowNelecHelper] = useState(false)
  const [nelec, setNelec] = useState('')
  const [noncolin, setNoncolin] = useState(false)
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
    bandFile.length > 0 &&
    latticeConstant !== '' &&
    vbmIndex !== ''

  function handleCelldm1Change(value) {
    setCelldm1Bohr(value)
    const parsed = parseFloat(value)
    if (!Number.isNaN(parsed)) setLatticeConstant((parsed * BOHR_TO_ANGSTROM).toFixed(6))
  }

  function handleNelecChange(value, noncolinValue) {
    setNelec(value)
    const parsed = parseFloat(value)
    if (!Number.isNaN(parsed)) setVbmIndex(String(Math.round(parsed / (noncolinValue ? 1 : 2))))
  }

  async function handleSubmit() {
    setError('')
    setJobStatus('processing')
    try {
      const formData = new FormData()
      formData.append('moduleId', module.id)
      formData.append('moduleTitle', module.title)

      const parameters = {
        directionLabel,
        latticeConstant,
        vbmIndex,
        nBandsBelowVbm, nBandsAboveCbm, pointsAroundExtremum,
        materialLabel,
        figureFormat,
        xRange, yRange,
      }
      formData.append('parameters', JSON.stringify(parameters))

      if (bandFile[0]) formData.append('bandFile', bandFile[0])
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
        <h2>1. This direction</h2>
        <p className="manual-help">
          One k-direction per run. Want more than one? Submit this form again for the next
          direction once this one's done — each run downloads its own zip with that
          direction's mass value and fit plot. Each file below can be uploaded (default) or
          pasted, independently.
        </p>
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

        <FileSlot label="Band-structure data file" filename="band-data.dat.gnu"
                  placeholder={'0.000000  -5.432100\n0.012345  -5.431000\n...'}
                  onFilesChange={setBandFile} />

        <div className="param-field" style={{ marginTop: 12 }}>
          <label>Lattice constant a (Angstrom)</label>
          <input type="text" value={latticeConstant} onChange={(e) => setLatticeConstant(e.target.value)} />
          <button type="button" className="link-button"
                  onClick={() => setShowCelldmHelper((v) => !v)}>
            {showCelldmHelper ? 'Hide' : "Don't know it in Angstrom? Derive from celldm(1)"}
          </button>
          {showCelldmHelper && (
            <div className="param-field" style={{ marginTop: 4 }}>
              <label>celldm(1) (Bohr, from your scf/bands input file's &amp;SYSTEM block)</label>
              <input type="text" value={celldm1Bohr} onChange={(e) => handleCelldm1Change(e.target.value)} />
            </div>
          )}
        </div>

        <div className="param-field">
          <label>VBM band index</label>
          <input type="number" value={vbmIndex} onChange={(e) => setVbmIndex(e.target.value)} />
          <button type="button" className="link-button"
                  onClick={() => setShowNelecHelper((v) => !v)}>
            {showNelecHelper ? 'Hide' : "Don't know the band index? Derive from electron count"}
          </button>
          {showNelecHelper && (
            <div style={{ marginTop: 4 }}>
              <div className="param-field">
                <label>Number of electrons (from your bands.out file)</label>
                <input type="text" value={nelec} onChange={(e) => handleNelecChange(e.target.value, noncolin)} />
              </div>
              <div className="param-field">
                <label>
                  <input type="checkbox" checked={noncolin}
                         onChange={(e) => { setNoncolin(e.target.checked); handleNelecChange(nelec, e.target.checked) }} />
                  {' '}Spin-orbit / noncolinear calculation (noncolin = .true.)
                </label>
              </div>
            </div>
          )}
        </div>
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
