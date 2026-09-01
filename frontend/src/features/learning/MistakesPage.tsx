import { CheckCircle2, RotateCcw } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { api } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'
import { AccountRequired } from './ProgressPage'
import type { Mistake, Skill } from './types'

const labels: Record<Skill, string> = { listening: 'Listening', reading: 'Reading', writing: 'Writing', speaking: 'Speaking' }

export function MistakesPage() {
  const { status } = useAuth()
  const [items, setItems] = useState<Mistake[]>([])
  const [stateFilter, setStateFilter] = useState<'open' | 'resolved' | 'all'>('open')
  const [skill, setSkill] = useState<'all' | Skill>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    if (status !== 'authenticated') return
    api.get<{ results: Mistake[] }>('/me/mistakes/').then((data) => setItems(data.results)).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Could not load mistakes.')).finally(() => setLoading(false))
  }, [status])
  const filtered = useMemo(() => items.filter((item) => (stateFilter === 'all' || item.state === stateFilter) && (skill === 'all' || item.skill === skill)).sort((a, b) => Number(Boolean(b.due_for_review)) - Number(Boolean(a.due_for_review))), [items, skill, stateFilter])
  async function changeState(item: Mistake) {
    const next = item.state === 'open' ? 'resolved' : 'open'
    try { const updated = await api.patch<Mistake>(`/me/mistakes/${item.id}/`, { state: next }); setItems((current) => current.map((candidate) => candidate.id === item.id ? updated : candidate)) } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not update this mistake.') }
  }
  if (status === 'loading') return <p role="status" className="py-16 text-center text-muted">Loading mistake bank…</p>
  if (status !== 'authenticated') return <AccountRequired title="Mistake Bank" />
  return <div className="mx-auto max-w-5xl space-y-6 animate-fade-up"><header><p className="eyebrow">Turn errors into review</p><h1 className="mt-1 text-3xl font-bold text-ink">Mistake Bank</h1><p className="mt-2 text-muted">Repeated misses merge into one pattern. Due mistakes appear first so you can review, retry the original set, then resolve the pattern when you can answer it confidently.</p></header><div className="flex flex-wrap gap-3"><label className="text-sm font-semibold text-muted">Status<select className="ml-2 rounded-input border border-line bg-surface p-2 text-ink" value={stateFilter} onChange={(event) => setStateFilter(event.target.value as typeof stateFilter)}><option value="open">Open</option><option value="resolved">Resolved</option><option value="all">All</option></select></label><label className="text-sm font-semibold text-muted">Skill<select className="ml-2 rounded-input border border-line bg-surface p-2 text-ink" value={skill} onChange={(event) => setSkill(event.target.value as typeof skill)}><option value="all">All</option>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label></div>{error && <p role="alert" className="rounded-input bg-bad-soft p-3 text-bad">{error}</p>}{loading ? <p role="status">Loading…</p> : filtered.length ? <div className="space-y-4">{filtered.map((item) => <Card key={item.id} className="p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wider text-accent">{labels[item.skill]} · {item.task_title}</p><h2 className="mt-1 text-lg font-bold text-ink">{item.stem}</h2></div><div className="flex items-center gap-2"><span className="rounded-full bg-bad-soft px-3 py-1 text-xs font-bold text-bad">Seen {item.occurrences}×</span>{item.due_for_review && <span className="rounded-full bg-warning-soft px-3 py-1 text-xs font-bold text-warn">Due now</span>}</div></div><dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2"><div className="rounded-input bg-bad-soft p-3"><dt className="font-bold text-bad">Your answer</dt><dd className="mt-1 text-ink">{item.selected}</dd></div><div className="rounded-input bg-good-soft p-3"><dt className="font-bold text-good">Correct answer</dt><dd className="mt-1 text-ink">{item.correct}</dd></div></dl><p className="mt-3 text-sm leading-6 text-muted">{item.explanation}</p><p className="mt-2 text-xs text-muted">{item.review_count ?? 0} review{item.review_count === 1 ? '' : 's'} recorded</p><div className="mt-4 flex flex-wrap gap-2"><Button variant="secondary" onClick={() => void changeState(item)}>{item.state === 'open' ? <CheckCircle2 size={17} /> : <RotateCcw size={17} />}{item.state === 'open' ? 'Mark reviewed' : 'Reopen'}</Button><Link className="btn-primary" to={item.destination ?? (item.skill === 'reading' ? '/practice' : `/practice/${item.skill}`)}>Retry this set</Link></div></Card>)}</div> : <Card className="p-6 text-center"><CheckCircle2 className="mx-auto text-good" size={30} /><h2 className="mt-2 text-xl font-bold text-ink">Nothing in this view</h2><p className="mt-1 text-sm text-muted">Complete objective practice to build your review queue.</p></Card>}</div>
}
