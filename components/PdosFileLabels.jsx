'use client'
import { useLang } from '@/lib/LangContext'

// For the pDOS plotter: each uploaded projwfc.x pdos_atm file needs an explicit
// species/orbital/shell label rather than relying on its filename surviving intact.
export default function PdosFileLabels({ files, labels, onChange }) {
  const { t } = useLang()

  function updateLabel(index, field, value) {
    const next = files.map((_, i) => labels[i] || { species: '', orbital: '', shell: '' })
    next[index] = { ...next[index], [field]: value }
    onChange(next)
  }

  if (files.length === 0) return null

  return (
    <div className="section-block" style={{ marginTop: 16 }}>
      <h2>{t('pdosLabelTitle')}</h2>
      <p style={{ fontSize: '0.9em', opacity: 0.8 }}>{t('pdosLabelDesc')}</p>
      <table className="pdos-label-table">
        <thead>
          <tr>
            <th>{t('pdosColFile')}</th>
            <th>{t('pdosColSpecies')}</th>
            <th>{t('pdosColOrbital')}</th>
            <th>{t('pdosColShell')}</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file, i) => {
            const label = labels[i] || { species: '', orbital: '', shell: '' }
            return (
              <tr key={`${file.name}-${i}`}>
                <td>{file.name}</td>
                <td>
                  <input
                    type="text"
                    value={label.species}
                    onChange={(e) => updateLabel(i, 'species', e.target.value)}
                    placeholder="Zn"
                  />
                </td>
                <td>
                  <input
                    type="text"
                    value={label.orbital}
                    onChange={(e) => updateLabel(i, 'orbital', e.target.value)}
                    placeholder="s"
                    maxLength={1}
                  />
                </td>
                <td>
                  <input
                    type="text"
                    value={label.shell}
                    onChange={(e) => updateLabel(i, 'shell', e.target.value)}
                    placeholder="4"
                  />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
