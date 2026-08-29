import { BookOpenCheck, Clock3, GraduationCap, Play, Target } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { useAuth } from '../auth/AuthProvider'
import { ApiError, api } from '../../lib/api'
import type {
  Paginated,
  ReadingCatalogItem,
  ReadingSession,
  ReadingTaskType,
  SessionMode,
} from './types'

const difficultyLabel = { 1: 'Foundation', 2: 'Developing', 3: 'Challenge' } as const

export function ReadingCatalogPage({ mode }: { mode: SessionMode }) {
  const navigate = useNavigate()
  const { status: authStatus } = useAuth()
  const [taskTypes, setTaskTypes] = useState<ReadingTaskType[]>([])
  const [items, setItems] = useState<ReadingCatalogItem[]>([])
  const [taskFilter, setTaskFilter] = useState('all')
  const [difficulty, setDifficulty] = useState('all')
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([
      api.get<ReadingTaskType[]>('/content/task-types/'),
      api.get<Paginated<ReadingCatalogItem>>('/content/reading/'),
    ])
      .then(([types, catalog]) => {
        if (!active) return
        setTaskTypes(types)
        setItems(catalog.results)
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Could not load Reading practice.')
      })
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [])

  const filtered = useMemo(
    () =>
      items.filter(
        (item) =>
          (taskFilter === 'all' || item.task_type === taskFilter) &&
          (difficulty === 'all' || item.difficulty === Number(difficulty)),
      ),
    [items, taskFilter, difficulty],
  )

  async function begin(item: ReadingCatalogItem) {
    setStarting(item.slug)
    setError('')
    try {
      const session = await api.post<ReadingSession>('/sessions/', {
        content_slug: item.slug,
        mode,
        time_limit_seconds: 900,
      })
      if (session.guest_token) {
        sessionStorage.setItem(`celpip-guest-${session.id}`, session.guest_token)
      }
      navigate(`/reading/session/${session.id}`, { state: { session } })
    } catch (reason) {
      setError(
        reason instanceof ApiError ? reason.message : 'The session could not be started. Please try again.',
      )
    } finally {
      setStarting(null)
    }
  }

  const isLearn = mode === 'learn'
  return (
    <div className="mx-auto w-full max-w-6xl space-y-8 animate-fade-up">
      <header className="rounded-card bg-brand px-5 py-8 text-white shadow-elevated sm:px-8">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent-soft">
          {isLearn ? 'Understand before you practise' : 'Timed, targeted preparation'}
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
          Reading {isLearn ? 'Learn' : 'Practice'}
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-white/80 sm:text-base">
          Work with original Canadian-context material across all four CELPIP-General Reading task
          families. {isLearn ? 'Get feedback after every answer.' : 'Corrections stay hidden until you submit.'}
        </p>
      </header>

      {isLearn && <TaskGuides taskTypes={taskTypes} />}

      <section aria-labelledby="reading-sets-title" className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="eyebrow">Original reviewed content</p>
            <h2 id="reading-sets-title" className="mt-1 text-2xl font-bold text-ink">
              Choose a Reading set
            </h2>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-xs font-semibold text-muted">
              Task type
              <select
                className="mt-1 min-h-11 w-full rounded-input border border-line bg-surface px-3 text-sm text-ink"
                value={taskFilter}
                onChange={(event) => setTaskFilter(event.target.value)}
              >
                <option value="all">All four parts</option>
                {taskTypes.map((task) => (
                  <option key={task.code} value={task.code}>Part {task.part_number}: {task.title}</option>
                ))}
              </select>
            </label>
            <label className="text-xs font-semibold text-muted">
              Difficulty
              <select
                className="mt-1 min-h-11 w-full rounded-input border border-line bg-surface px-3 text-sm text-ink"
                value={difficulty}
                onChange={(event) => setDifficulty(event.target.value)}
              >
                <option value="all">All levels</option>
                <option value="1">Foundation</option>
                <option value="2">Developing</option>
                <option value="3">Challenge</option>
              </select>
            </label>
          </div>
        </div>

        {error && <p role="alert" className="rounded-input bg-bad-soft p-3 text-sm text-bad">{error}</p>}
        {loading ? (
          <p role="status" className="py-10 text-center text-muted">Loading reviewed Reading sets…</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {filtered.map((item) => {
              const task = taskTypes.find((candidate) => candidate.code === item.task_type)
              return (
                <Card key={item.slug} className="flex h-full flex-col p-5 transition hover:-translate-y-0.5 hover:shadow-card-hover">
                  <div className="flex items-start justify-between gap-3">
                    <span className="rounded-full bg-brand-soft px-3 py-1 text-xs font-bold text-brand">
                      Part {task?.part_number ?? '–'}
                    </span>
                    <span className="text-xs font-semibold text-muted">{difficultyLabel[item.difficulty]}</span>
                  </div>
                  <h3 className="mt-4 text-xl font-bold text-ink">{item.title}</h3>
                  <p className="mt-1 text-sm text-muted">{task?.title} · {item.topic}</p>
                  <div className="mt-4 flex flex-wrap gap-3 text-xs text-muted">
                    <span className="inline-flex items-center gap-1"><Target size={15} /> Practice level {item.estimated_level}</span>
                    <span className="inline-flex items-center gap-1"><Clock3 size={15} /> {isLearn ? 'Untimed' : '15-minute practice timer'}</span>
                  </div>
                  <Button
                    className="mt-6 w-full sm:w-auto sm:self-start"
                    variant={isLearn ? 'accent' : 'primary'}
                    disabled={authStatus === 'loading' || starting !== null}
                    onClick={() => begin(item)}
                  >
                    {isLearn ? <GraduationCap size={18} /> : <Play size={18} />}
                    {starting === item.slug ? 'Starting…' : isLearn ? 'Learn with this set' : 'Start timed practice'}
                  </Button>
                </Card>
              )
            })}
          </div>
        )}
        {!loading && filtered.length === 0 && (
          <p className="rounded-card border border-line bg-surface p-8 text-center text-muted">No sets match these filters.</p>
        )}
      </section>
    </div>
  )
}

function TaskGuides({ taskTypes }: { taskTypes: ReadingTaskType[] }) {
  return (
    <section aria-labelledby="task-guides-title">
      <p className="eyebrow">Know the four parts</p>
      <h2 id="task-guides-title" className="mt-1 text-2xl font-bold text-ink">Task-type guides</h2>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {taskTypes.map((task) => (
          <details key={task.code} className="card group p-5">
            <summary className="flex cursor-pointer list-none items-center gap-3 font-bold text-ink focus-visible:outline-2 focus-visible:outline-brand">
              <BookOpenCheck className="text-accent" size={21} />
              <span>Part {task.part_number}: {task.title}</span>
              <span aria-hidden="true" className="ml-auto text-muted transition group-open:rotate-45">+</span>
            </summary>
            <p className="mt-3 text-sm leading-6 text-muted">{task.description}</p>
            <h3 className="mt-4 text-sm font-bold text-ink">A reliable approach</h3>
            <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-muted">
              {task.strategy.map((step) => <li key={step}>{step}</li>)}
            </ol>
            <h3 className="mt-4 text-sm font-bold text-ink">Watch for</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
              {task.common_mistakes.map((mistake) => <li key={mistake}>{mistake}</li>)}
            </ul>
          </details>
        ))}
      </div>
    </section>
  )
}
