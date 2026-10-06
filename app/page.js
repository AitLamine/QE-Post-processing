'use client'
import CategorySection from '@/components/CategorySection'
import { CATEGORIES } from '@/lib/modules'
import { useLang } from '@/lib/LangContext'

export default function HomePage() {
  const { t } = useLang()
  return (
    <div>
      <div className="intro">
        <h1>DFT Post-Processing Lab</h1>
        <p>{t('intro1')}</p>
        <p>{t('intro2')}</p>
      </div>
      {CATEGORIES.map((category) => (
        <CategorySection key={category.id} category={category} />
      ))}
    </div>
  )
}
