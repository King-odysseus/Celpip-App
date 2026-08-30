import { Clock3, GraduationCap, PenLine, Play, Search, Target } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { useAuth } from '../auth/AuthProvider'
import { ApiError, api, fetchAllPages } from '../../lib/api'
import type {
  SessionMode,
  StartedWritingSession,
  WritingCatalogItem,
  WritingTaskType,
} from './types'

const difficultyLabel = { 1: 'Foundation', 2: 'Developing', 3: 'Challenge' } as const

// Suggested per-task practice durations (public format guidance). Keyed by the
// stable task-type code so we do not need to fetch each prompt to start a timer.
const DURATION_SECONDS: Record<string, number> = {
  writing_email: 27 * 60,
  writing_survey: 26 * 60,
}

function durationLabel(taskCode: string): string {
  const minutes = Math.round((DURATION_SECONDS[taskCode] ?? 27 * 60) / 60)
  return `${minutes}-minute suggested`
}

export function WritingCatalogPage({ mode }: { mode: SessionMode }) {
  const navigate = useNavigate()
  const { status: authStatus } = useAuth()
  const [taskTypes, setTaskTypes] = useState<WritingTaskType[]>([])
  const [items, setItems] = useState<WritingCatalogItem[]>([])
  const [taskFilter, setTaskFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([
      api.get<WritingTaskType[]>('/content/task-types/?skill=writing'),
      fetchAllPages<WritingCatalogItem>('/content/writing/'),
    ])
      .then(([types, catalog]) => {
        if (!active) return
        setTaskTypes(types)
        setItems(catalog)
      })
      .catch((reason: unknown) =>
        active && setError(reason instanceof Error ? reason.message : 'Could not load Writing practice.'),
      )
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [])

  const filtered = useMemo(
    () => items.filter((item) => (taskFilter === 'all' || item.task_type === taskFilter) && `${item.title} ${item.topic}`.toLowerCase().includes(search.trim().toLowerCase())),
    [items, taskFilter, search],
  )

  async function begin(item: WritingCatalogItem) {
    setStarting(item.slug)
    setError('')
    try {
      const session = await api.post<StartedWritingSession>('/sessions/', {
        content_slug: item.slug,
        mode,
        time_limit_seconds: DURATION_SECONDS[item.task_type] ?? 27 * 60,
      })
      if (session.guest_token) {
        sessionStorage.setItem(`celpip-guest-${session.id}`, session.guest_token)
      }
      navigate(`/writing/session/${session.id}`)
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
          Writing {isLearn ? 'Learn' : 'Practice'}
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-white/80 sm:text-base">
          Write original responses for both CELPIP-General Writing tasks — an email and a survey
          response. Aim for 150–200 words. {isLearn
            ? 'Take your time and use the guidance as you draft.'
            : 'A suggested timer runs while you write; your draft autosaves as you go.'}
        </p>
        <nav aria-label="Skill switch" className="mt-5 flex flex-wrap gap-2">
          <SkillLink active={false} to={isLearn ? '/learn' : '/practice'}>Reading</SkillLink>
          <SkillLink active={false} to={isLearn ? '/learn/listening' : '/practice/listening'}>Listening</SkillLink>
          <SkillLink active to={isLearn ? '/learn/writing' : '/practice/writing'}>Writing</SkillLink>
          <SkillLink active={false} to={isLearn ? '/learn/speaking' : '/practice/speaking'}>Speaking</SkillLink>
        </nav>
      </header>

      {isLearn && <TaskGuides taskTypes={taskTypes} />}

      <section aria-labelledby="writing-sets-title" className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="eyebrow">Original reviewed Writing prompts</p>
            <h2 id="writing-sets-title" className="mt-1 text-2xl font-bold text-ink">
              Choose a Writing prompt
            </h2>
          </div>
          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
          <label className="text-xs font-semibold text-muted">
            Search prompts
            <span className="relative mt-1 block"><Search aria-hidden="true" size={16} className="pointer-events-none absolute left-3 top-3 text-muted" /><input aria-label="Search prompts" className="min-h-11 w-full rounded-input border border-line bg-surface pl-9 pr-3 text-sm text-ink sm:w-56" placeholder="Title or topic" value={search} onChange={(event) => setSearch(event.target.value)} /></span>
          </label>
          <label className="text-xs font-semibold text-muted">
            Task type
            <select
              className="mt-1 min-h-11 w-full rounded-input border border-line bg-surface px-3 text-sm text-ink sm:w-56"
              value={taskFilter}
              onChange={(event) => setTaskFilter(event.target.value)}
            >
              <option value="all">Both tasks</option>
              {taskTypes.map((task) => (
                <option key={task.code} value={task.code}>Task {task.part_number}: {task.title}</option>
              ))}
            </select>
          </label>
          </div>
        </div>

        {error && <p role="alert" className="rounded-input bg-bad-soft p-3 text-sm text-bad">{error}</p>}
        {loading ? (
          <p role="status" className="py-10 text-center text-muted">Loading reviewed Writing prompts…</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {filtered.map((item) => {
              const task = taskTypes.find((candidate) => candidate.code === item.task_type)
              return (
                <Card key={item.slug} className="flex h-full flex-col p-5 transition hover:-translate-y-0.5 hover:shadow-card-hover">
                  <div className="flex items-start justify-between gap-3">
                    <span className="rounded-full bg-brand-soft px-3 py-1 text-xs font-bold text-brand">
                      Task {task?.part_number ?? '–'}
                    </span>
                    <span className="text-xs font-semibold text-muted">{difficultyLabel[item.difficulty]}</span>
                  </div>
                  <h3 className="mt-4 text-xl font-bold text-ink">{item.title}</h3>
                  <p className="mt-1 text-sm text-muted">{task?.title} · {item.topic}</p>
                  <div className="mt-4 flex flex-wrap gap-3 text-xs text-muted">
                    <span className="inline-flex items-center gap-1"><Target size={15} /> Target 150–200 words</span>
                    <span className="inline-flex items-center gap-1">
                      <Clock3 size={15} /> {isLearn ? 'Untimed' : durationLabel(item.task_type)}
                    </span>
                  </div>
                  <Button
                    className="mt-6 w-full sm:w-auto sm:self-start"
                    variant={isLearn ? 'accent' : 'primary'}
                    disabled={authStatus === 'loading' || starting !== null}
                    onClick={() => begin(item)}
                  >
                    {isLearn ? <GraduationCap size={18} /> : <Play size={18} />}
                    {starting === item.slug ? 'Starting…' : isLearn ? 'Learn with this prompt' : 'Start timed practice'}
                  </Button>
                </Card>
              )
            })}
          </div>
        )}
        {!loading && filtered.length === 0 && (
          <p className="rounded-card border border-line bg-surface p-8 text-center text-muted">No prompts match this filter.</p>
        )}
      </section>
    </div>
  )
}

function TaskGuides({ taskTypes }: { taskTypes: WritingTaskType[] }) {
  return (
    <section aria-labelledby="writing-guides-title">
      <p className="eyebrow">Know the two tasks</p>
      <h2 id="writing-guides-title" className="mt-1 text-2xl font-bold text-ink">Task-type guides</h2>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {taskTypes.map((task) => (
          <details key={task.code} className="card group p-5">
            <summary className="flex cursor-pointer list-none items-center gap-3 font-bold text-ink focus-visible:outline-2 focus-visible:outline-brand">
              <PenLine className="text-accent" size={21} />
              <span>Task {task.part_number}: {task.title}</span>
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

function SkillLink({ active, to, children }: { active: boolean; to: string; children: string }) {
  return (
    <Link
      to={to}
      aria-current={active ? 'page' : undefined}
      className={`rounded-full px-4 py-2 text-sm font-bold transition ${
        active ? 'bg-white text-brand' : 'bg-white/10 text-white hover:bg-white/20'
      }`}
    >
      {children}
    </Link>
  )
}
