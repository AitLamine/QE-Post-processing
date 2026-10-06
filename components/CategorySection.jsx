'use client'
import Link from 'next/link'
import StatusBadge from './StatusBadge'
import { useLang } from '@/lib/LangContext'
import { categoryName, categoryDescription, moduleTitle, moduleOutputDescription } from '@/lib/translations'

export default function CategorySection({ category }) {
  const { lang } = useLang()
  const desc = categoryDescription(category, lang)

  return (
    <section className="category">
      <div className="category-header">
        <h2>{categoryName(category, lang)}</h2>
        {desc && <p>{desc}</p>}
      </div>
      <div className="module-grid">
        {category.modules.map((module) => (
          <Link key={module.id} href={`/task/${module.id}`} className="module-card">
            <h3>{moduleTitle(module, lang)}</h3>
            <p>{moduleOutputDescription(module, lang)}</p>
            <StatusBadge status={module.status} />
          </Link>
        ))}
      </div>
    </section>
  )
}
