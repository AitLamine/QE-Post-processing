import { notFound } from 'next/navigation'
import TaskPage from '@/components/TaskPage'
import { getAllModules, getModuleById } from '@/lib/modules'

export function generateStaticParams() {
  return getAllModules().map((module) => ({ id: module.id }))
}

export default function Task({ params }) {
  const module = getModuleById(params.id)
  if (!module) notFound()
  return <TaskPage module={module} />
}
