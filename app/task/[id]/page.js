import { notFound } from 'next/navigation'
import TaskPage from '@/components/TaskPage'
import { getAllModules, getModuleById } from '@/lib/modules'

export function generateStaticParams() {
  return getAllModules().map((module) => ({ id: module.id }))
}

export default async function Task({ params }) {
  const { id } = await params
  const module = getModuleById(id)
  if (!module) notFound()
  return <TaskPage module={module} />
}
