'use client'
import { useLang } from '@/lib/LangContext'

// Manual-entry counterpart to PdosFileLabels: instead of uploading one projwfc.x pdos_atm
// file per orbital/atom, the student pastes each one's raw content directly, still labeled
// with the same species/orbital/shell fields the backend needs.
export default function ManualPdosEntries({ entries, onChange }) {
  const { t } = useLang()

  function updateEntry(index, patch) {
    onChange(entries.map((e, i) => (i === index ? { ...e, ...patch } : e)))
  }

  function addEntry() {
    onChange([...entries, { species: '', orbital: '', shell: '', text: '' }])
  }

  function removeEntry(index) {
    onChange(entries.filter((_, i) => i !== index))
  }

  return (
    <div>
      {entries.map((entry, i) => (
        <div className="section-block" key={i} style={{ marginTop: i === 0 ? 0 : 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <h2 style={{ marginBottom: 0 }}>Entry {i + 1}</h2>
            {entries.length > 1 && (
              <button className="btn-action" onClick={() => removeEntry(i)}>{t('manualPdosRemoveButton')}</button>
            )}
          </div>
          <table className="pdos-label-table" style={{ marginTop: 10 }}>
            <thead>
              <tr>
                <th>Species (e.g. Zn)</th>
                <th>Orbital (s/p/d/f)</th>
                <th>Shell number (e.g. 4)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <input type="text" value={entry.species} placeholder="Zn"
                         onChange={(e) => updateEntry(i, { species: e.target.value })} />
                </td>
                <td>
                  <input type="text" value={entry.orbital} placeholder="s" maxLength={1}
                         onChange={(e) => updateEntry(i, { orbital: e.target.value })} />
                </td>
                <td>
                  <input type="text" value={entry.shell} placeholder="4"
                         onChange={(e) => updateEntry(i, { shell: e.target.value })} />
                </td>
              </tr>
            </tbody>
          </table>
          <div className="param-field" style={{ marginTop: 10 }}>
            <label>pdos_atm file content</label>
            <textarea
              className="manual-paste-textarea"
              rows={6}
              value={entry.text}
              placeholder={'# E (eV)   ldos(E)\n-10.000   0.0012\n-9.950    0.0015\n...'}
              onChange={(e) => updateEntry(i, { text: e.target.value })}
            />
          </div>
        </div>
      ))}
      <button className="btn-action" onClick={addEntry}>{t('manualPdosAddButton')}</button>
    </div>
  )
}
