import { CalendarRange, CheckCircle2, RefreshCcw } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { api } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'
import { AccountRequired } from './ProgressPage'
import type { StudyPlan, StudyTask } from './types'

export function StudyPlanPage() {
  const { status } = useAuth()
  const [plan, setPlan] = useState<StudyPlan | null>(null)
  const [error, setError] = useState('')
  const [regenerating, setRegenerating] = useState(false)
  useEffect(() => { if (status === 'authenticated') api.get<StudyPlan>('/me/study-plan/').then(setPlan).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Could not load your plan.')) }, [status])
  const groups = useMemo(() => { const result = new Map<string, StudyTask[]>(); for (const task of plan?.tasks ?? []) result.set(task.scheduled_date, [...(result.get(task.scheduled_date) ?? []), task]); return [...result.entries()] }, [plan])
  async function setState(task: StudyTask, state: StudyTask['state']) { try { const result = await api.patch<{ state: StudyTask['state']; completed_at: string | null }>(`/me/study-plan/tasks/${task.id}/`, { state }); setPlan((current) => current ? { ...current, tasks: current.tasks.map((item) => item.id === task.id ? { ...item, ...result } : item) } : current) } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not update the task.') } }
  async function regenerate() { setRegenerating(true); try { setPlan(await api.post<StudyPlan>('/me/study-plan/')) } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not rebuild the plan.') } finally { setRegenerating(false) } }
  if (status === 'loading') return <p role="status" className="py-16 text-center text-muted">Loading study plan…</p>
  if (status !== 'authenticated') return <AccountRequired title="Study Plan" />
  return <div className="mx-auto max-w-6xl space-y-6 animate-fade-up"><header className="flex flex-wrap items-end justify-between gap-4"><div><p className="eyebrow">Explainable daily actions</p><h1 className="mt-1 text-3xl font-bold text-ink">Study Plan</h1><p className="mt-2 max-w-3xl text-muted">Your schedule follows your preferred days and minutes. Weaker or unpractised skills come first without starving stronger skills.</p></div><Button variant="secondary" disabled={regenerating} onClick={() => void regenerate()}><RefreshCcw className={regenerating ? 'animate-spin' : ''} size={17} /> Rebuild plan</Button></header>{error && <p role="alert" className="rounded-input bg-bad-soft p-3 text-bad">{error}</p>}{!plan ? <p role="status" className="py-10 text-center text-muted">Generating your first plan…</p> : <><Card className="p-5"><h2 className="flex items-center gap-2 text-xl font-bold text-ink"><CalendarRange size={21} /> Plan version {plan.version}</h2><p className="mt-2 text-sm text-muted">{plan.reason_summary.rule}</p><p className="mt-1 text-xs text-muted">Based on {plan.reason_summary.source_attempts} completed attempt(s). Every recommendation displays its reason.</p></Card><div className="space-y-6">{groups.map(([date, tasks]) => <section key={date}><h2 className="text-xl font-bold text-ink">{new Date(`${date}T12:00:00`).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}</h2><div className="mt-3 grid gap-3 md:grid-cols-2">{tasks.map((task) => <Card key={task.id} className={`p-5 ${task.state === 'completed' ? 'border-good/30 bg-good-soft/30' : ''}`}><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wider text-accent">{task.skill} · {task.minutes} min</p><h3 className="mt-1 font-bold text-ink">{task.title}</h3></div>{task.state === 'completed' && <CheckCircle2 className="text-good" size={22} />}</div><p className="mt-3 text-sm leading-6 text-muted">{task.reason}</p><div className="mt-4 flex flex-wrap gap-2"><Link className="btn-primary" to={task.destination}>Open practice</Link><Button variant="secondary" onClick={() => void setState(task, task.state === 'completed' ? 'pending' : 'completed')}>{task.state === 'completed' ? 'Undo' : 'Mark complete'}</Button></div></Card>)}</div></section>)}</div></>}</div>
}
