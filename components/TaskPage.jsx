'use client'
import Link from 'next/link'
import { useState } from 'react'
import UploadWidget from './UploadWidget'
import FileSlot from './FileSlot'
import PdosUploadSection from './PdosUploadSection'
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

  // Per-role file slots (band-dos, dielectric-function, optical-magnitudes, tauc-plot,
  // bader-charge, hubbard-u): each entry in module.manualEntryFiles gets its own FileSlot,
  // which independently offers "upload" (default) or "paste instead" for that one file --
  // not a whole-form mode, a per-field choice. Keyed by role (f.key) -> File[].
  const [slotFiles, setSlotFiles] = useState({})
  const [manualPdosEntries, setManualPdosEntries] = useState([{ species: '', orbital: '', shell: '', text: '' }])
  const [manualDosForFermiText, setManualDosForFermiText] = useState('')
  const [templateFile, setTemplateFile] = useState([])
  // Bumped by "Try with sample data"; each FileSlot (and PdosUploadSection, for pdos) reacts
  // to the change by filling itself in with real, validated example content.
  const [sampleTrigger, setSampleTrigger] = useState(0)

  const isPdosModule = module.id === 'pdos-plotter'
  // Custom-template upload is only meaningful for modules whose backend actually produces a
  // pgfplots figure (i.e. they expose a figureFormat choice); bader-charge/hubbard-u are
  // tables-only and effective-mass has its own separate form with its own upload already.
  const supportsLatexTemplate = module.parameters.some((p) => p.id === 'figureFormat')
  const hasFileSlots = !isPdosModule && module.manualEntryFiles?.length > 0

  function updateSlotFiles(key, nextFiles) {
    setSlotFiles((prev) => ({ ...prev, [key]: nextFiles }))
  }

  const slotFilesList = hasFileSlots
    ? (module.manualEntryFiles || []).map((f) => (slotFiles[f.key] || [])[0]).filter(Boolean)
    : []

  const manualPdosFiles = manualPdosEntries
    .filter((e) => e.text.trim())
    .map((e, i) => new File([e.text], `pasted-pdos-${i + 1}.dat`, { type: 'text/plain' }))

  const activeFiles = hasFileSlots ? slotFilesList : (isPdosModule ? manualPdosFiles : files)
  const activePdosLabels = isPdosModule
    ? manualPdosEntries.filter((e) => e.text.trim()).map((e) => ({ species: e.species, orbital: e.orbital, shell: e.shell }))
    : pdosLabels
  const activeDosForFermi = isPdosModule && manualDosForFermiText.trim()
    ? [new File([manualDosForFermiText], 'dos-for-fermi.dos', { type: 'text/plain' })]
    : dosForFermi

  const canSubmit = activeFiles.length > 0 && jobStatus !== 'processing'
  const inputFiles = moduleInputFiles(module, lang)

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
      if (hasFileSlots) {
        // Each slot's file goes under its own field name -- the backend knows exactly which
        // role each upload is by field name alone, no filename/content guessing needed.
        (module.manualEntryFiles || []).forEach((f) => {
          const file = (slotFiles[f.key] || [])[0]
          if (file) formData.append(f.key, file)
        })
      } else {
        activeFiles.forEach((file) => formData.append('files', file))
      }
      compareFiles.forEach((file) => formData.append('compareFiles', file))
      activeDosForFermi.forEach((file) => formData.append('dosForFermi', file))
      if (templateFile[0]) formData.append('templateFile', templateFile[0])

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

        {hasFileSlots ? (
          <>
            <p className="manual-help">{t('manualEntryIntro')}</p>
            {(module.manualEntryFiles || []).map((f) => (
              <FileSlot
                key={f.key}
                label={manualEntryLabel(module, f.key, f.label, lang)}
                filename={f.filename}
                placeholder={f.placeholder}
                sampleText={f.placeholder}
                fillTrigger={sampleTrigger}
                onFilesChange={(nextFiles) => updateSlotFiles(f.key, nextFiles)}
              />
            ))}
          </>
        ) : isPdosModule ? (
          <PdosUploadSection
            files={files}
            setFiles={setFiles}
            pdosLabels={pdosLabels}
            setPdosLabels={setPdosLabels}
            dosForFermi={dosForFermi}
            setDosForFermi={setDosForFermi}
            manualPdosEntries={manualPdosEntries}
            setManualPdosEntries={setManualPdosEntries}
            manualDosForFermiText={manualDosForFermiText}
            setManualDosForFermiText={setManualDosForFermiText}
            sampleTrigger={sampleTrigger}
            t={t}
          />
        ) : (
          <UploadWidget checklist={inputFiles} files={files} onChange={setFiles} />
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
        {(hasFileSlots || isPdosModule) && (
          <SampleDataLink onClick={() => setSampleTrigger((n) => n + 1)} />
        )}
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
        {supportsLatexTemplate && (
          <div style={{ marginTop: 16 }}>
            <UploadWidget
              label="Custom LaTeX template (optional, .tex) — your own pgfplots template; the generated axis is spliced in wherever it contains %%PGFPLOTS_AXIS%%, otherwise it's appended"
              files={templateFile}
              onChange={(f) => setTemplateFile(f.slice(-1))}
            />
          </div>
        )}
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
