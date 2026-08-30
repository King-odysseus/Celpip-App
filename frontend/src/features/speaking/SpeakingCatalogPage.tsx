import { Clock3, GraduationCap, Mic2, Play } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { ApiError, api, fetchAllPages } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'
import type {
  SessionMode,
  SpeakingCatalogItem,
  SpeakingTaskType,
  StartedSpeakingSession,
} from './types'

const difficultyLabel = { 1: 'Foundation', 2: 'Developing', 3: 'Challenge' } as const
const timings: Record<string, { prep: string; total: number; response: number }> = {
  speaking_advice: { prep: '30 sec prep', total: 120, response: 90 },
  speaking_experience: { prep: '30 sec prep', total: 90, response: 60 },
  speaking_scene: { prep: '30 sec prep', total: 90, response: 60 },
  speaking_predictions: { prep: '30 sec prep', total: 90, response: 60 },
  speaking_compare_persuade: { prep: '2 × 60 sec prep', total: 180, response: 60 },
  speaking_difficult_situation: { prep: '60 sec prep', total: 120, response: 60 },
  speaking_opinions: { prep: '30 sec prep', total: 120, response: 90 },
  speaking_unusual: { prep: '30 sec prep', total: 90, response: 60 },
}

export function SpeakingCatalogPage({ mode }: { mode: SessionMode }) {
  const navigate = useNavigate()
  const { status: authStatus } = useAuth()
  const [taskTypes, setTaskTypes] = useState<SpeakingTaskType[]>([])
  const [items, setItems] = useState<SpeakingCatalogItem[]>([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([
      api.get<SpeakingTaskType[]>('/content/task-types/?skill=speaking'),
      fetchAllPages<SpeakingCatalogItem>('/content/speaking/'),
    ])
      .then(([types, catalog]) => {
        if (active) {
          setTaskTypes(types)
          setItems(catalog)
        }
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Could not load Speaking practice.')
      })
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [])

  const filtered = useMemo(
    () => items.filter((item) => filter === 'all' || item.task_type === filter),
    [filter, items],
  )
  const isLearn = mode === 'learn'

  async function begin(item: SpeakingCatalogItem) {
    setStarting(item.slug)
    setError('')
    try {
      const format = timings[item.task_type] ?? { total: 120 }
      const session = await api.post<StartedSpeakingSession>('/sessions/', {
        content_slug: item.slug,
        mode,
        // Includes a private-upload grace period; the recorder itself uses the
        // exact official preparation and speaking countdowns.
        time_limit_seconds: format.total + 300,
      })
      if (session.guest_token) {
        sessionStorage.setItem(`celpip-guest-${session.id}`, session.guest_token)
      }
      navigate(`/speaking/session/${session.id}`)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'The session could not be started.')
    } finally {
      setStarting(null)
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-8 animate-fade-up">
      <header className="rounded-card bg-brand px-5 py-8 text-white shadow-elevated sm:px-8">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent-soft">
          {isLearn ? 'Understand, plan, then speak' : 'Official-format recording practice'}
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
          Speaking {isLearn ? 'Learn' : 'Practice'}
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-white/80 sm:text-base">
          Practise all eight CELPIP-General Speaking tasks with original prompts, exact task
          countdowns, private recordings, playback, and honest self-review.
        </p>
        <nav aria-label="Skill switch" className="mt-5 flex flex-wrap gap-2">
          <SkillLink to={isLearn ? '/learn' : '/practice'}>Reading</SkillLink>
          <SkillLink to={isLearn ? '/learn/listening' : '/practice/listening'}>Listening</SkillLink>
          <SkillLink to={isLearn ? '/learn/writing' : '/practice/writing'}>Writing</SkillLink>
          <SkillLink active to={isLearn ? '/learn/speaking' : '/practice/speaking'}>Speaking</SkillLink>
        </nav>
      </header>

      {isLearn && <TaskGuides taskTypes={taskTypes} />}

      <section aria-labelledby="speaking-prompts-title" className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="eyebrow">16 original reviewed prompts</p>
            <h2 id="speaking-prompts-title" className="mt-1 text-2xl font-bold text-ink">
              Choose a Speaking prompt
            </h2>
          </div>
          <label className="text-xs font-semibold text-muted">
            Task type
            <select
              className="mt-1 min-h-11 w-full rounded-input border border-line bg-surface px-3 text-sm text-ink sm:w-72"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            >
              <option value="all">All eight tasks</option>
              {taskTypes.map((task) => (
                <option key={task.code} value={task.code}>Task {task.part_number}: {task.title}</option>
              ))}
            </select>
          </label>
        </div>
        {error && <p role="alert" className="rounded-input bg-bad-soft p-3 text-sm text-bad">{error}</p>}
        {loading ? (
          <p role="status" className="py-10 text-center text-muted">Loading Speaking prompts…</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {filtered.map((item) => {
              const task = taskTypes.find((candidate) => candidate.code === item.task_type)
              const timing = timings[item.task_type]
              return (
                <Card key={item.slug} className="flex h-full flex-col p-5 transition hover:-translate-y-0.5 hover:shadow-card-hover">
                  <div className="flex items-start justify-between gap-3">
                    <span className="rounded-full bg-brand-soft px-3 py-1 text-xs font-bold text-brand">Task {task?.part_number}</span>
                    <span className="text-xs font-semibold text-muted">{difficultyLabel[item.difficulty]}</span>
                  </div>
                  <h3 className="mt-4 text-xl font-bold text-ink">{item.title}</h3>
                  <p className="mt-1 text-sm text-muted">{task?.title} · {item.topic}</p>
                  <p className="mt-4 flex items-center gap-2 text-xs text-muted">
                    <Clock3 size={15} /> {timing?.prep} · {timing?.response} sec response
                  </p>
                  <Button
                    className="mt-6 w-full sm:w-auto sm:self-start"
                    variant={isLearn ? 'accent' : 'primary'}
                    disabled={authStatus === 'loading' || starting !== null}
                    onClick={() => void begin(item)}
                  >
                    {isLearn ? <GraduationCap size={18} /> : <Play size={18} />}
                    {starting === item.slug ? 'Opening…' : isLearn ? 'Learn with this prompt' : 'Open microphone practice'}
                  </Button>
                </Card>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}

function TaskGuides({ taskTypes }: { taskTypes: SpeakingTaskType[] }) {
  return (
    <section aria-labelledby="speaking-guides-title">
      <p className="eyebrow">Know all eight tasks</p>
      <h2 id="speaking-guides-title" className="mt-1 text-2xl font-bold text-ink">Task-type guides</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {taskTypes.map((task) => (
          <details key={task.code} className="card group p-5">
            <summary className="flex cursor-pointer list-none items-center gap-3 font-bold text-ink focus-visible:outline-2 focus-visible:outline-brand">
              <Mic2 className="text-accent" size={20} />
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

function SkillLink({ to, active = false, children }: { to: string; active?: boolean; children: string }) {
  return (
    <Link
      to={to}
      aria-current={active ? 'page' : undefined}
      className={`rounded-full px-4 py-2 text-sm font-bold transition ${active ? 'bg-white text-brand' : 'bg-white/10 text-white hover:bg-white/20'}`}
    >
      {children}
    </Link>
  )
}
