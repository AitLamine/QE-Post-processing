'use client'
import Link from 'next/link'
import { useState } from 'react'
import UploadWidget from './UploadWidget'
import PdosFileLabels from './PdosFileLabels'
import ManualPdosEntries from './ManualPdosEntries'
import EffectiveMassForm from './EffectiveMassForm'
import ParameterForm from './ParameterForm'
import JobStatusIndicator from './JobStatusIndicator'
import SampleDataLink from './SampleDataLink'
import StatusBadge from './StatusBadge'
import { useLang } from '@/lib/LangContext'
import {
  categoryName,
  moduleTitle,
  moduleOutputDescription,
  moduleInputFiles,
  moduleCompareLabel,
  paramLabel,
  paramOptionLabel,
  manualEntryLabel,
} from '@/lib/translations'

function defaultValues(parameters) {
  const values = {}
  for (const param of parameters) values[param.id] = param.default
  return values
}

export default function TaskPage({ module }) {
  const { lang, t } = useLang()
  const [files, setFiles] = useState([])
  const [compareFiles, setCompareFiles] = useState([])
  const [pdosLabels, setPdosLabels] = useState([])
  const [dosForFermi, setDosForFermi] = useState([])
  const [values, setValues] = useState(() => defaultValues(module.parameters))
  const [jobStatus, setJobStatus] = useState('idle')
  const [error, setError] = useState('')

  // Secondary input mode: paste raw file content instead of uploading, for students who'd
  // rather not hand over their actual calculation/structure files. "upload" stays the
  // default/primary path with unchanged behavior; everything below only applies when the
  // student explicitly switches to "manual".
  const [inputMode, setInputMode] = useState('upload')
  const [manualTexts, setManualTexts] = useState({})
  const [manualPdosEntries, setManualPdosEntries] = useState([{ species: '', orbital: '', shell: '', text: '' }])
  const [manualDosForFermiText, setManualDosForFermiText] = useState('')

  const isPdosModule = module.id === 'pdos-plotter'
  const hasManualMode = isPdosModule || (module.manualEntryFiles?.length > 0)

  const manualFiles = (module.manualEntryFiles || [])
    .filter((f) => (manualTexts[f.key] || '').trim())
    .map((f) => new File([manualTexts[f.key]], f.filename, { type: 'text/plain' }))

  const manualPdosFiles = manualPdosEntries
    .filter((e) => e.text.trim())
    .map((e, i) => new File([e.text], `pasted-pdos-${i + 1}.dat`, { type: 'text/plain' }))

  const activeFiles = inputMode === 'upload' ? files : (isPdosModule ? manualPdosFiles : manualFiles)
  const activePdosLabels = inputMode === 'upload'
    ? pdosLabels
    : manualPdosEntries.filter((e) => e.text.trim()).map((e) => ({ species: e.species, orbital: e.orbital, shell: e.shell }))
  const activeDosForFermi = inputMode === 'upload'
    ? dosForFermi
    : (manualDosForFermiText.trim() ? [new File([manualDosForFermiText], 'dos-for-fermi.dos', { type: 'text/plain' })] : [])

  const canSubmit = activeFiles.length > 0 && jobStatus !== 'processing'
  const inputFiles = moduleInputFiles(module, lang)

  function updateManualText(key, text) {
    setManualTexts((prev) => ({ ...prev, [key]: text }))
  }

  async function handleSubmit() {
    setError('')
    setJobStatus('processing')
    try {
      const formData = new FormData()
      formData.append('moduleId', module.id)
      formData.append('moduleTitle', module.title)
      const submittedValues = isPdosModule
        ? { ...values, pdosFileLabels: activeFiles.map((f, i) => ({ filename: f.name, ...(activePdosLabels[i] || {}) })) }
        : values
      formData.append('parameters', JSON.stringify(submittedValues))
      activeFiles.forEach((file) => formData.append('files', file))
      compareFiles.forEach((file) => formData.append('compareFiles', file))
      activeDosForFermi.forEach((file) => formData.append('dosForFermi', file))

      const res = await fetch(module.apiEndpoint || '/api/process', { method: 'POST', body: formData })
      if (!res.ok) throw new Error(`Server returned ${res.status}`)

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
      setError(t('errorMessage'))
      setJobStatus('failed')
    }
  }

  return (
    <div>
      <div className="task-header">
        <div className="breadcrumb">
          <Link href="/">← {t('breadcrumbAll')}</Link> / {categoryName({ id: module.categoryId, name: module.category }, lang)}
        </div>
        <h1>{moduleTitle(module, lang)}</h1>
        <p className="output-desc">{moduleOutputDescription(module, lang)}</p>
        <div style={{ marginTop: 8 }}><StatusBadge status={module.status} /></div>
      </div>

      {module.status === 'candidate' && <div className="notice">{t('noticeCandidate')}</div>}
      {module.needsReview && <div className="notice warn">{t('noticeReview')}</div>}

      {module.id === 'effective-mass-extractor' ? (
        <EffectiveMassForm module={module} />
      ) : (
        <>
      <div className="section-block">
        <h2>{t('sectionUpload')}</h2>
        {hasManualMode && (
          <div className="input-mode-toggle">
            <label className={`mode-toggle-option${inputMode === 'upload' ? ' checked' : ''}`}>
              <input type="radio" name="inputMode" checked={inputMode === 'upload'} onChange={() => setInputMode('upload')} />
              {t('modeUploadLabel')}
            </label>
            <label className={`mode-toggle-option${inputMode === 'manual' ? ' checked' : ''}`}>
              <input type="radio" name="inputMode" checked={inputMode === 'manual'} onChange={() => setInputMode('manual')} />
              {t('modeManualLabel')}
            </label>
          </div>
        )}

        {inputMode === 'upload' || !hasManualMode ? (
          <>
            <UploadWidget checklist={inputFiles} files={files} onChange={setFiles} />
            {isPdosModule && (
              <>
                <PdosFileLabels files={files} labels={pdosLabels} onChange={setPdosLabels} />
                <div style={{ marginTop: 16 }}>
                  <UploadWidget
                    label="dos.x output (optional — only used to auto-detect the VBM/Fermi energy)"
                    files={dosForFermi}
                    onChange={setDosForFermi}
                  />
                </div>
              </>
            )}
          </>
        ) : (
          <div className="manual-entry">
            <p className="manual-help">{t('manualEntryIntro')}</p>
            {isPdosModule ? (
              <>
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
              </>
            ) : (
              (module.manualEntryFiles || []).map((f) => (
                <div className="param-field" key={f.key} style={{ marginTop: 12 }}>
                  <label>{manualEntryLabel(module, f.key, f.label, lang)}</label>
                  <textarea
                    className="manual-paste-textarea"
                    rows={8}
                    value={manualTexts[f.key] || ''}
                    onChange={(e) => updateManualText(f.key, e.target.value)}
                    placeholder={f.placeholder}
                  />
                </div>
              ))
            )}
          </div>
        )}

        {module.compareMode && (
          <div style={{ marginTop: 16 }}>
            <UploadWidget
              label={moduleCompareLabel(module, lang) || t('compareDefaultLabel')}
              checklist={inputFiles}
              files={compareFiles}
              onChange={setCompareFiles}
            />
          </div>
        )}
        <SampleDataLink />
      </div>

      <div className="section-block">
        <h2>{t('sectionParameters')}</h2>
        <ParameterForm
          parameters={module.parameters}
          values={values}
          onChange={setValues}
          getLabel={(param) => paramLabel(module, param, lang)}
          getOptionLabel={(param, opt) => paramOptionLabel(module, param, opt, lang)}
        />
      </div>

      <div className="section-block">
        <h2>{t('sectionProcess')}</h2>
        <button className="btn-primary" disabled={!canSubmit} onClick={handleSubmit}>
          {t('submitButton')}
        </button>
        <JobStatusIndicator status={jobStatus} />
        {error && <div className="error-message">{error}</div>}
      </div>
        </>
      )}
    </div>
  )
}
