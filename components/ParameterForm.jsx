'use client'
import { useLang } from '@/lib/LangContext'

export default function ParameterForm({ parameters, values, onChange, getLabel, getOptionLabel }) {
  const { t } = useLang()
  const label = getLabel || ((param) => param.label)
  const optionLabel = getOptionLabel || ((param, opt) => opt)

  if (!parameters || parameters.length === 0) {
    return <p className="no-params-note">{t('noParamsNote')}</p>
  }

  function setValue(id, value) {
    onChange({ ...values, [id]: value })
  }

  return (
    <div>
      {parameters.map((param) => {
        const value = values[param.id]
        if (param.type === 'select') {
          return (
            <div className="param-field" key={param.id}>
              <label htmlFor={param.id}>{label(param)}</label>
              <select id={param.id} value={value} onChange={(e) => setValue(param.id, e.target.value)}>
                {param.options.map((opt) => (
                  <option key={opt} value={opt}>{optionLabel(param, opt)}</option>
                ))}
              </select>
            </div>
          )
        }
        if (param.type === 'multiselect') {
          const selected = value || []
          return (
            <div className="param-field" key={param.id}>
              <label>{label(param)}</label>
              <div className="multiselect-options">
                {param.options.map((opt) => {
                  const checked = selected.includes(opt)
                  return (
                    <label key={opt} className={`multiselect-option${checked ? ' checked' : ''}`}>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {
                          setValue(
                            param.id,
                            checked ? selected.filter((o) => o !== opt) : [...selected, opt]
                          )
                        }}
                      />
                      {optionLabel(param, opt)}
                    </label>
                  )
                })}
              </div>
            </div>
          )
        }
        if (param.type === 'number') {
          return (
            <div className="param-field" key={param.id}>
              <label htmlFor={param.id}>{label(param)}</label>
              <input
                id={param.id}
                type="number"
                value={value}
                onChange={(e) => setValue(param.id, e.target.value)}
              />
            </div>
          )
        }
        if (param.type === 'checkbox') {
          return (
            <div className="param-field checkbox-row" key={param.id}>
              <input
                id={param.id}
                type="checkbox"
                checked={!!value}
                onChange={(e) => setValue(param.id, e.target.checked)}
              />
              <label htmlFor={param.id} style={{ marginBottom: 0 }}>{label(param)}</label>
            </div>
          )
        }
        return (
          <div className="param-field" key={param.id}>
            <label htmlFor={param.id}>{label(param)}</label>
            <input
              id={param.id}
              type="text"
              value={value}
              onChange={(e) => setValue(param.id, e.target.value)}
            />
          </div>
        )
      })}
    </div>
  )
}
