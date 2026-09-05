import {
  ArrowRight,
  CheckCircle2,
  Clock3,
  History,
  Info,
  ListChecks,
  Play,
  Timer,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, ButtonLink, Card } from '../../components/ui'
import { ApiError, api } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'
import { createMock, listMocks, updateMockSchedule, type CompactFocus } from './api'
import {
  COMPACT_SCOPE,
  COMPACT_SCOPE_LIMITATION,
  COMPONENT_META,
  COMPONENT_ORDER,
  FULL_LENGTH_SCOPE,
  FULL_LENGTH_SCOPE_LIMITATION,
  OFFICIAL_SOURCE_URL,
} from './constants'
import type { MockAttempt, MockState } from './types'

const STATE_LABEL: Record<MockState, string> = {
  ready: 'Ready to start',
  active: 'In progress',
  between_sections: 'Between components',
  completed: 'Completed',
  abandoned: 'Abandoned',
}

function stateTone(state: MockState): string {
  if (state === 'completed') return 'bg-good-soft text-good'
  if (state === 'active' || state === 'between_sections') return 'bg-brand-soft text-brand'
  if (state === 'abandoned') return 'bg-bad-soft text-bad'
  return 'bg-surface-secondary text-muted'
}

export function MockTestsPage() {
  const { status } = useAuth()

  if (status === 'loading') {
    return <p role="status" className="py-16 text-center text-muted">Checking your session…</p>
  }
  if (status === 'anonymous') {
    return <AnonymousMockCta />
  }
  return <MockHub />
}

function MockHeader() {
  return (
    <header className="rounded-card bg-brand px-5 py-8 text-white shadow-elevated sm:px-8">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent-soft">
        Full four-component simulation
      </p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Mock Tests</h1>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-white/80 sm:text-base">
        Work through Listening → Reading → Writing → Speaking in official order, with
        server-timed section boxes and results released only after every component finishes.
      </p>
    </header>
  )
}

function CompactScopeCard() {
  return (
    <Card className="border-warn/40">
      <div className="flex items-start gap-3">
        <Info size={20} className="mt-0.5 shrink-0 text-warn" aria-hidden="true" />
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-ink">Two ways to practice</h2>
          <p className="mt-1 text-sm leading-6 text-muted">{COMPACT_SCOPE_LIMITATION}</p>
          <p className="mt-2 text-sm leading-6 text-muted">{FULL_LENGTH_SCOPE_LIMITATION}</p>
          <p className="mt-2 text-sm">
            <a
              href={OFFICIAL_SOURCE_URL}
              target="_blank"
              rel="noreferrer"
              className="font-semibold text-brand hover:underline"
            >
              View the official test format
            </a>
          </p>
        </div>
      </div>
    </Card>
  )
}

function OfficialFormatCard() {
  return (
    <Card>
      <div className="flex items-start gap-3">
        <ListChecks size={20} className="mt-0.5 shrink-0 text-accent" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold tracking-tight text-ink">Official component order and timing</h2>
          <ol className="mt-3 space-y-2">
            {COMPONENT_ORDER.map((skill, index) => (
              <li key={skill} className="flex items-center gap-3 rounded-input border border-line bg-surface-secondary px-3 py-2.5">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand text-xs font-bold text-white tabular-nums">
                  {index + 1}
                </span>
                <span className="flex-1 font-semibold text-ink">{COMPONENT_META[skill].label}</span>
                <span className="inline-flex items-center gap-1 text-sm text-muted tabular-nums">
                  <Clock3 size={15} /> {COMPONENT_META[skill].timingLabel}
                </span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </Card>
  )
}

function AnonymousMockCta() {
  return (
    <section aria-labelledby="mock-title" className="space-y-5 animate-fade-up">
      <MockHeader />
      <Card className="border-brand/30 bg-brand-soft/40">
        <p className="text-sm text-ink">
          Full mock attempts are saved to your account so you can pause, resume, and receive
          component results. You are browsing without an account — create a free one to start a
          mock, or sign in to resume an existing attempt.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <ButtonLink to="/register">
            Create a free account <ArrowRight size={17} />
          </ButtonLink>
          <ButtonLink to="/signin" variant="secondary">
            Sign in
          </ButtonLink>
        </div>
      </Card>
      <CompactScopeCard />
      <OfficialFormatCard />
    </section>
  )
}

function MockHub() {
  const navigate = useNavigate()
  const [attempts, setAttempts] = useState<MockAttempt[]>([])
  const [loading, setLoading] = useState(true)
  const [creatingScope, setCreatingScope] = useState<string | null>(null)
  const [compactMode, setCompactMode] = useState<CompactFocus['mode']>('recommended')
  const [compactSkills, setCompactSkills] = useState<string[]>([])
  const [taskTypes, setTaskTypes] = useState<Array<{ code: string; skill: string; title: string }>>([])
  const [compactTaskTypes, setCompactTaskTypes] = useState<string[]>([])
  const [fullMockDate, setFullMockDate] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    listMocks()
      .then((data) => active && setAttempts(data.results))
      .catch((reason: unknown) =>
        active && setError(reason instanceof Error ? reason.message : 'Could not load your mock attempts.'),
      )
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    Promise.all(['listening', 'reading', 'writing', 'speaking'].map((skill) =>
      api.get<Array<{ code: string; skill: string; title: string }>>(`/content/task-types/?skill=${skill}`),
    )).then((groups) => setTaskTypes(groups.flat())).catch(() => setTaskTypes([]))
  }, [])

  async function create(scope: string, focus?: CompactFocus, scheduledFor?: string) {
    setCreatingScope(scope)
    setError('')
    try {
      const attempt = await createMock(scope, focus, scheduledFor)
      navigate(`/mock/${attempt.id}`)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'The mock could not be created.')
      setCreatingScope(null)
    }
  }

  async function removeSchedule(attemptId: string) {
    try {
      const updated = await updateMockSchedule(attemptId, null)
      setAttempts((current) => current.map((attempt) => attempt.id === attemptId ? updated : attempt))
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'The schedule could not be changed.')
    }
  }

  return (
    <section aria-labelledby="mock-title" className="space-y-5 animate-fade-up">
      <MockHeader />

      <CompactScopeCard />
      <OfficialFormatCard />

      <Card>
        <h2 className="text-lg font-semibold tracking-tight text-ink">Start a new mock</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div className="rounded-input border border-line p-4">
            <p className="font-semibold text-ink">Compact mock</p>
            <p className="mt-1 text-sm text-muted">
              A focused, approximately one-hour rehearsal. Choose a balanced mix, let your recent mistakes guide it, or select skills yourself.
            </p>
            <div className="mt-3 flex flex-wrap gap-2" aria-label="Compact mock focus">
              {([
                ['recommended', 'Recommended'],
                ['balanced', 'Balanced'],
                ['custom', 'Choose skills'],
              ] as const).map(([mode, label]) => (
                <button key={mode} type="button" onClick={() => setCompactMode(mode)} className={`rounded-full px-3 py-1.5 text-xs font-bold ${compactMode === mode ? 'bg-brand text-white' : 'bg-surface-secondary text-muted hover:bg-brand-soft'}`}>
                  {label}
                </button>
              ))}
            </div>
            {compactMode === 'custom' && (
              <div className="mt-3 space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-2">
                {(['listening', 'reading', 'writing', 'speaking'] as const).map((skill) => (
                  <label key={skill} className="flex items-center gap-2 rounded-input border border-line px-2 py-2 capitalize">
                    <input type="checkbox" checked={compactSkills.includes(skill)} onChange={() => { setCompactSkills((current) => current.includes(skill) ? current.filter((item) => item !== skill) : [...current, skill]); setCompactTaskTypes([]) }} />
                    {skill}
                  </label>
                ))}
              </div>
              {compactSkills.length > 0 && taskTypes.length > 0 && (
                <details className="rounded-input border border-line p-3">
                  <summary className="cursor-pointer font-semibold text-ink">Choose specific task types (optional)</summary>
                  <p className="mt-2 text-xs text-muted">Selecting task types makes the compact mock use exactly those types.</p>
                  <div className="mt-2 space-y-2">
                    {taskTypes.filter((task) => compactSkills.includes(task.skill)).map((task) => (
                      <label key={task.code} className="flex items-start gap-2">
                        <input className="mt-1" type="checkbox" checked={compactTaskTypes.includes(task.code)} onChange={() => setCompactTaskTypes((current) => current.includes(task.code) ? current.filter((code) => code !== task.code) : [...current, task.code])} />
                        <span>{task.title}</span>
                      </label>
                    ))}
                  </div>
                </details>
              )}
              </div>
            )}
            <Button
              className="mt-3 w-full"
              variant="secondary"
              disabled={creatingScope !== null || (compactMode === 'custom' && compactSkills.length === 0)}
              onClick={() => void create(COMPACT_SCOPE, { mode: compactMode, skills: compactMode === 'custom' ? compactSkills : undefined, task_types: compactMode === 'custom' && compactTaskTypes.length ? compactTaskTypes : undefined })}
            >
              {creatingScope === COMPACT_SCOPE ? 'Creating…' : <><Play size={18} /> Build compact mock</>}
            </Button>
          </div>
          <div className="rounded-input border border-brand/40 bg-brand-soft/30 p-4">
            <p className="flex items-center gap-2 font-semibold text-ink">
              Full simulation
              <span className="rounded-full bg-brand px-2 py-0.5 text-[11px] font-bold text-white">Unofficial</span>
            </p>
            <p className="mt-1 text-sm text-muted">
              Current official Listening/Reading question counts and every Speaking task —
              the full-length exam-day rehearsal.
            </p>
            <label className="mt-3 block text-xs font-semibold text-ink">
              Schedule for a specific day <span className="font-normal text-muted">(optional)</span>
              <input type="date" value={fullMockDate} onChange={(event) => setFullMockDate(event.target.value)} className="mt-1 block w-full rounded-input border border-line bg-surface px-3 py-2 text-sm" />
            </label>
            <Button
              className="mt-3 w-full"
              disabled={creatingScope !== null}
              onClick={() => void create(FULL_LENGTH_SCOPE, undefined, fullMockDate || undefined)}
            >
              {creatingScope === FULL_LENGTH_SCOPE ? 'Creating…' : <><Play size={18} /> Full simulation</>}
            </Button>
          </div>
        </div>
        {error && <p role="alert" className="mt-3 rounded-input bg-bad-soft p-3 text-sm text-bad">{error}</p>}
      </Card>

      <section aria-labelledby="mock-history-title" className="space-y-3">
        <div className="flex items-center gap-2">
          <History size={18} className="text-accent" aria-hidden="true" />
          <h2 id="mock-history-title" className="text-2xl font-bold text-ink">Your mock history</h2>
        </div>

        {loading ? (
          <p role="status" className="py-8 text-center text-muted">Loading your mock attempts…</p>
        ) : attempts.length === 0 ? (
          <p className="rounded-card border border-line bg-surface p-8 text-center text-muted">
            No mock attempts yet. Create one to begin your first full simulation.
          </p>
        ) : (
          <ul className="space-y-3">
            {attempts.map((attempt) => (
              <li key={attempt.id}>
                <Card className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-full px-3 py-1 text-xs font-bold ${stateTone(attempt.state)}`}>
                        {STATE_LABEL[attempt.state]}
                      </span>
                      <span className="rounded-full bg-surface-secondary px-2 py-0.5 text-[11px] font-semibold text-muted">
                        {attempt.scope === FULL_LENGTH_SCOPE ? 'Full simulation' : 'Compact mock'}
                      </span>
                      <span className="text-xs text-muted">
                        {attempt.started_at
                          ? `Started ${formatDate(attempt.started_at)}`
                          : `Created ${formatDate(attempt.created_at)}`}
                      </span>
                      {attempt.scheduled_for && attempt.state === 'ready' && (
                        <span className="text-xs font-semibold text-brand">Scheduled for {formatDate(attempt.scheduled_for)}</span>
                      )}
                    </div>
                    <p className="mt-2 text-sm text-muted">
                      {attempt.state === 'completed'
                        ? `All four components finished${attempt.completed_at ? ` · ${formatDate(attempt.completed_at)}` : ''}.`
                        : attempt.state === 'active'
                          ? `Task ${attempt.current_order} of ${attempt.progress.total} · ${attempt.progress.completed} complete`
                          : `${attempt.progress.total} tasks · Listening → Reading → Writing → Speaking`}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 self-start sm:self-center">
                  {attempt.scheduled_for && attempt.state === 'ready' && (
                    <Button variant="ghost" onClick={() => void removeSchedule(attempt.id)}>Remove date</Button>
                  )}
                  <Button variant={attempt.state === 'completed' ? 'secondary' : 'primary'} onClick={() => navigate(`/mock/${attempt.id}`)}>
                    {attempt.state === 'completed' ? (
                      <><CheckCircle2 size={17} /> View results</>
                    ) : attempt.state === 'active' || attempt.state === 'between_sections' ? (
                      <><Timer size={17} /> Resume</>
                    ) : (
                      <><ArrowRight size={17} /> Open</>
                    )}
                  </Button>
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  )
}

function formatDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}
