import {
  AlertTriangle,
  ArrowLeft,
  Award,
  CheckCircle2,
  Clock3,
  ListChecks,
  Play,
  RefreshCcw,
  SkipForward,
  Timer,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Card, Meter } from '../../components/ui'
import { ApiError } from '../../lib/api'
import { getMock, getMockResults, startMock } from './api'
import { COMPONENT_META, COMPONENT_ORDER } from './constants'
import type {
  MockAttempt,
  MockComponent,
  MockCurrentTask,
  MockResults,
  MockTask,
  MockTaskState,
  Skill,
} from './types'

const TASK_STATE_TONE: Record<MockTaskState, string> = {
  pending: 'border-line bg-surface text-muted',
  current: 'border-brand bg-brand-soft text-brand',
  submitted: 'border-good/40 bg-good-soft text-good',
  skipped: 'border-bad/40 bg-bad-soft text-bad',
}

export function MockWorkspacePage() {
  const { attemptId = '' } = useParams()
  const navigate = useNavigate()

  const [attempt, setAttempt] = useState<MockAttempt | null>(null)
  const [results, setResults] = useState<MockResults | null>(null)
  const [error, setError] = useState('')
  const [starting, setStarting] = useState(false)

  const loadAttempt = useCallback(async () => {
    if (!attemptId) return
    try {
      const loaded = await getMock(attemptId)
      setAttempt(loaded)
      setError('')
      if (loaded.state === 'completed') {
        try {
          setResults(await getMockResults(attemptId))
        } catch {
          // Results may still be releasing; the completed banner covers it.
          setResults(null)
        }
      }
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Could not open this mock attempt.')
    }
  }, [attemptId])

  useEffect(() => {
    void loadAttempt()
  }, [loadAttempt])

  async function handleStart() {
    setStarting(true)
    setError('')
    try {
      setAttempt(await startMock(attemptId))
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'The mock could not be started.')
    } finally {
      setStarting(false)
    }
  }

  function launchCurrent(task: MockCurrentTask) {
    const sessionId = task.session_id
    if (task.section === 'listening' || task.section === 'reading') {
      navigate(`/reading/session/${sessionId}`)
    } else if (task.section === 'writing') {
      navigate(`/writing/session/${sessionId}`)
    } else {
      navigate(`/speaking/session/${sessionId}`)
    }
  }

  if (error && !attempt) {
    return <WorkspaceError message={error} onBack={() => navigate('/mock')} />
  }
  if (!attempt) {
    return <p role="status" className="py-16 text-center text-muted">Loading your mock attempt…</p>
  }

  return (
    <div className="mx-auto w-full max-w-5xl animate-fade-in">
      <header className="mb-4 flex flex-wrap items-center gap-3 rounded-card border border-line bg-surface px-4 py-3 shadow-card">
        <Button variant="ghost" onClick={() => navigate('/mock')}>
          <ArrowLeft size={17} /> Exit
        </Button>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase tracking-wider text-accent">Mock attempt</p>
          <h1 className="truncate font-bold text-ink">Listening → Reading → Writing → Speaking</h1>
        </div>
        <span className="rounded-full bg-brand-soft px-3 py-1.5 text-sm font-bold text-brand">
          {attempt.progress.completed}/{attempt.progress.total} tasks
        </span>
      </header>

      {attempt.state === 'completed' ? (
        <CompletedView attempt={attempt} results={results} onBack={() => navigate('/mock')} />
      ) : attempt.state === 'active' ? (
        <ActiveView
          attempt={attempt}
          error={error}
          onLaunch={launchCurrent}
          onRefresh={loadAttempt}
        />
      ) : attempt.state === 'ready' ? (
        <ReadyView
          attempt={attempt}
          starting={starting}
          error={error}
          onStart={handleStart}
        />
      ) : (
        <IdleView attempt={attempt} onRefresh={loadAttempt} />
      )}
    </div>
  )
}

function ReadyView({
  attempt,
  starting,
  error,
  onStart,
}: {
  attempt: MockAttempt
  starting: boolean
  error: string
  onStart: () => void
}) {
  return (
    <div className="space-y-5">
      <Card className="text-center">
        <p className="eyebrow">Ready when you are</p>
        <h2 className="mt-2 text-2xl font-bold text-ink">Your mock is assembled</h2>
        <p className="mx-auto mt-2 max-w-2xl text-sm leading-6 text-muted">
          All 20 task families are frozen in official order. Starting begins the Listening
          section and its server-managed time box; leaving mid-section marks unfinished tasks
          as skipped when time runs out.
        </p>
        <div className="mt-6 flex justify-center">
          <Button disabled={starting} onClick={onStart}>
            <Play size={18} /> {starting ? 'Starting…' : 'Start mock'}
          </Button>
        </div>
        {error && <p role="alert" className="mx-auto mt-4 max-w-xl rounded-input bg-bad-soft p-3 text-sm text-bad">{error}</p>}
      </Card>
      <TaskProgress tasks={attempt.tasks ?? []} />
      <DisclaimerNote text={attempt.disclaimer} />
    </div>
  )
}

function ActiveView({
  attempt,
  error,
  onLaunch,
  onRefresh,
}: {
  attempt: MockAttempt
  error: string
  onLaunch: (task: MockCurrentTask) => void
  onRefresh: () => void
}) {
  const current = attempt.current_task
  return (
    <div className="space-y-5">
      {attempt.section_deadline_at && (
        <Card className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Clock3 size={20} className="text-accent" aria-hidden="true" />
            <div>
              <p className="text-sm font-bold text-ink">
                {attempt.current_section
                  ? `${COMPONENT_META[attempt.current_section as Skill]?.label ?? 'Section'} time`
                  : 'Section time'}
              </p>
              <p className="text-xs text-muted">Managed by the server; ends when the box expires.</p>
            </div>
          </div>
          <SectionTimer
            deadline={attempt.section_deadline_at}
            serverNow={attempt.server_now}
            onExpire={onRefresh}
          />
        </Card>
      )}

      <Card>
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold tracking-tight text-ink">Progress</h2>
          <span className="text-sm font-semibold text-muted tabular-nums">
            {attempt.progress.completed} of {attempt.progress.total} complete
          </span>
        </div>
        <div className="mt-3">
          <Meter
            value={attempt.progress.completed}
            max={attempt.progress.total}
            label={`Mock progress: ${attempt.progress.completed} of ${attempt.progress.total} tasks`}
          />
        </div>
      </Card>

      {current ? (
        <Card className="border-brand/40">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="eyebrow">
                {COMPONENT_META[current.section]?.label} · Task {current.order} of 20
              </p>
              <h2 className="mt-1 text-xl font-bold text-ink">{current.title}</h2>
              <p className="mt-1 text-sm text-muted">
                {current.kind === 'objective'
                  ? 'Answer each question in this set, then submit to continue.'
                  : current.kind === 'writing'
                    ? 'Write and submit your response to continue.'
                    : 'Record and submit your response to continue.'}
              </p>
            </div>
            <Button className="self-start" onClick={() => onLaunch(current)}>
              <Play size={18} /> Launch task
            </Button>
          </div>
          {error && <p role="alert" className="mt-3 rounded-input bg-bad-soft p-3 text-sm text-bad">{error}</p>}
        </Card>
      ) : (
        <Card className="text-center">
          <p className="text-muted">No current task. Refresh to reconcile with the server.</p>
          <Button variant="secondary" className="mt-4" onClick={onRefresh}>
            <RefreshCcw size={17} /> Refresh
          </Button>
        </Card>
      )}

      <TaskProgress tasks={attempt.tasks ?? []} />
      <DisclaimerNote text={attempt.disclaimer} />
    </div>
  )
}

function IdleView({ attempt, onRefresh }: { attempt: MockAttempt; onRefresh: () => void }) {
  return (
    <Card className="text-center">
      <p className="eyebrow">Between components</p>
      <h2 className="mt-2 text-2xl font-bold text-ink">
        {attempt.state === 'between_sections' ? 'Preparing the next component' : 'Attempt unavailable'}
      </h2>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-muted">
        Refresh to reconcile this attempt with the server.
      </p>
      <Button variant="secondary" className="mt-5" onClick={onRefresh}>
        <RefreshCcw size={17} /> Refresh
      </Button>
    </Card>
  )
}

function CompletedView({
  attempt,
  results,
  onBack,
}: {
  attempt: MockAttempt
  results: MockResults | null
  onBack: () => void
}) {
  return (
    <div className="space-y-5 animate-fade-up">
      <Card className="overflow-hidden p-0 text-center">
        <div className="bg-brand px-5 py-8 text-white">
          <p className="flex items-center justify-center gap-2 text-xs font-bold uppercase tracking-widest text-accent-soft">
            <Award size={17} /> Mock complete
          </p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight">Four component results</h2>
          <p className="mt-2 text-sm text-white/80">
            CELPIP reports each skill separately. No overall score is calculated.
          </p>
        </div>
        <p className="p-4 text-sm text-muted">{results?.disclaimer ?? attempt.disclaimer}</p>
      </Card>

      {results ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {results.components.map((component) => (
            <ComponentCard key={component.skill} component={component} />
          ))}
        </div>
      ) : (
        <p role="status" className="py-8 text-center text-muted">Releasing your component results…</p>
      )}

      <div className="flex flex-wrap gap-3">
        <Button onClick={onBack}>Back to Mock Tests</Button>
      </div>
    </div>
  )
}

function ComponentCard({ component }: { component: MockComponent }) {
  const label = COMPONENT_META[component.skill]?.label ?? component.skill
  return (
    <Card>
      <h3 className="text-lg font-bold text-ink">{label}</h3>
      {component.measure === 'practice_accuracy' ? (
        <div className="mt-3">
          <p className="text-3xl font-bold tabular-nums text-ink">
            {component.raw_correct}/{component.raw_possible}
          </p>
          <p className="mt-1 text-sm text-muted">
            {component.accuracy_percent === null
              ? 'Practice accuracy'
              : `${component.accuracy_percent}% practice accuracy`}
          </p>
        </div>
      ) : (
        <div className="mt-3">
          <p className="text-3xl font-bold tabular-nums text-ink">
            {component.estimate_low === null || component.estimate_high === null
              ? 'Pending'
              : `≈ ${component.estimate_low}–${component.estimate_high}`}
          </p>
          <p className="mt-1 text-sm text-muted">
            AI-assisted practice estimate · {component.feedback_ready}/{component.tasks_total} tasks
          </p>
        </div>
      )}
    </Card>
  )
}

function TaskProgress({ tasks }: { tasks: MockTask[] }) {
  return (
    <section aria-labelledby="task-progress-title" className="space-y-3">
      <div className="flex items-center gap-2">
        <ListChecks size={18} className="text-accent" aria-hidden="true" />
        <h2 id="task-progress-title" className="text-2xl font-bold text-ink">Task families</h2>
      </div>
      {COMPONENT_ORDER.map((skill) => {
        const group = tasks.filter((task) => task.section === skill)
        if (group.length === 0) return null
        return (
          <Card key={skill}>
            <h3 className="text-sm font-bold text-ink">{COMPONENT_META[skill].label}</h3>
            <ol className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6">
              {group.map((task) => (
                <li
                  key={task.order}
                  title={task.title}
                  className={`flex min-h-11 items-center justify-center gap-1.5 rounded-input border px-2 py-1.5 text-center text-xs font-semibold ${TASK_STATE_TONE[task.state]}`}
                >
                  <span className="tabular-nums">{task.order}</span>
                  {task.state === 'current' && <Play size={13} aria-hidden="true" />}
                  {task.state === 'submitted' && <CheckCircle2 size={13} aria-hidden="true" />}
                  {task.state === 'skipped' && <SkipForward size={13} aria-hidden="true" />}
                </li>
              ))}
            </ol>
          </Card>
        )
      })}
    </section>
  )
}

function DisclaimerNote({ text }: { text: string }) {
  return (
    <p className="rounded-input border border-info/30 bg-info-bg p-4 text-sm leading-6 text-ink">
      {text}
    </p>
  )
}

function SectionTimer({
  deadline,
  serverNow,
  onExpire,
}: {
  deadline: string
  serverNow: string
  onExpire: () => void
}) {
  const clockOffset = useMemo(() => Date.now() - new Date(serverNow).getTime(), [serverNow])
  const compute = useCallback(
    () => Math.max(0, Math.ceil((new Date(deadline).getTime() - (Date.now() - clockOffset)) / 1000)),
    [deadline, clockOffset],
  )
  const [seconds, setSeconds] = useState(compute)
  const firedRef = useRef(false)

  useEffect(() => {
    const tick = () => {
      const next = compute()
      setSeconds(next)
      if (next === 0 && !firedRef.current) {
        firedRef.current = true
        onExpire()
      }
    }
    const timer = window.setInterval(tick, 1000)
    return () => window.clearInterval(timer)
  }, [compute, onExpire])

  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60
  const announcement =
    seconds === 300 ? 'Five minutes remaining' : seconds === 60 ? 'One minute remaining' : seconds === 0 ? 'Time has ended' : ''

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full px-3 py-2 text-sm font-bold tabular-nums ${
        seconds <= 60 ? 'bg-bad-soft text-bad' : 'bg-brand-soft text-brand'
      }`}
    >
      <Timer size={17} aria-hidden="true" />
      <span aria-label={`${minutes} minutes ${remainder} seconds remaining`}>
        {minutes}:{String(remainder).padStart(2, '0')}
      </span>
      <span className="sr-only" aria-live="polite">{announcement}</span>
    </div>
  )
}

function WorkspaceError({ message, onBack }: { message: string; onBack: () => void }) {
  return (
    <Card className="mx-auto max-w-xl text-center">
      <p className="flex items-center justify-center gap-2 text-bad">
        <AlertTriangle size={20} /> Mock unavailable
      </p>
      <p role="alert" className="mt-3 text-muted">{message}</p>
      <Button className="mt-6" onClick={onBack}>Back to Mock Tests</Button>
    </Card>
  )
}
