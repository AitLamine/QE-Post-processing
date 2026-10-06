import JSZip from 'jszip'
import { getModuleById } from '@/lib/modules'

export async function POST(request) {
  const formData = await request.formData()
  const moduleId = formData.get('moduleId')
  const moduleTitle = formData.get('moduleTitle') || moduleId
  const parameters = JSON.parse(formData.get('parameters') || '{}')
  const files = formData.getAll('files')
  const compareFiles = formData.getAll('compareFiles')

  const module = getModuleById(moduleId)

  const zip = new JSZip()

  const paramLines = Object.entries(parameters)
    .map(([key, value]) => `  - ${key}: ${Array.isArray(value) ? value.join(', ') : value}`)
    .join('\n')

  const fileLines = files.map((f) => `  - ${f.name}`).join('\n') || '  (none)'
  const compareLines = compareFiles.map((f) => `  - ${f.name}`).join('\n')

  const readme = [
    `${moduleTitle} — Results`,
    '',
    'STATUS: processing not implemented yet.',
    'This zip previews the folder structure the real module will produce once its script is',
    'adopted into the app. Nothing in figures/, tables/, or raw-parsed-data/ is real output.',
    '',
    'Uploaded files:',
    fileLines,
    ...(compareFiles.length ? ['', 'Compare-against files:', compareLines] : []),
    '',
    'Parameters used:',
    paramLines || '  (none)',
    '',
    `Expected output once implemented: ${module ? module.outputDescription : 'n/a'}`,
    '',
  ].join('\n')

  zip.file('README.txt', readme)
  zip.folder('figures')
  zip.folder('tables')
  zip.folder('raw-parsed-data')

  const buffer = await zip.generateAsync({ type: 'nodebuffer' })

  return new Response(buffer, {
    status: 200,
    headers: {
      'Content-Type': 'application/zip',
      'Content-Disposition': `attachment; filename="${(moduleTitle || 'Results').replace(/[^a-z0-9]+/gi, '-')}-Results.zip"`,
    },
  })
}
