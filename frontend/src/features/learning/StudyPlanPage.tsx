import {
  CalendarRange,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Flame,
  RefreshCcw,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Card, CardTitle } from '../../components/ui'
import { api } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'
import { AccountRequired } from './ProgressPage'
import type { Skill, StudyPlan, StudyTask } from './types'

const SKILLS: Skill[] = ['listening', 'reading', 'writing', 'speaking']

// One distinguishable dot colour per skill; `info`, `good`, `warning`, and
// `brand` come from the design tokens so they adapt to the active theme.
const SKILL_DOT: Record<Skill, string> = {
  listening: 'bg-info',
  reading: 'bg-good',
  writing: 'bg-warning',
  speaking: 'bg-brand',
}

const SKILL_LABEL: Record<Skill, string> = {
  listening: 'Listening',
  reading: 'Reading',
  writing: 'Writing',
  speaking: 'Speaking',
}

function dayParts(date: string): { day: string } {
  const value = new Date(`${date}T12:00:00`)
  return {
    day: value.toLocaleDateString(undefined, { day: 'numeric' }),
  }
}

/** Calendar showing which skills were completed on each day + the streak. */
function StreakBar({ plan }: { plan: StudyPlan }) {
  const { streak, days } = plan.consistency
  const today = plan.consistency.today
  const monthGroups = new Map<string, typeof days>()
  for (const day of days) {
    const month = day.date.slice(0, 7)
    monthGroups.set(month, [...(monthGroups.get(month) ?? []), day])
  }
  const availableMonths = [...monthGroups.keys()]
  const initialMonthIndex = Math.max(0, availableMonths.indexOf(today.slice(0, 7)))
  const [selectedMonth, setSelectedMonth] = useState(today.slice(0, 7))
  const selectedMonthIndex = Math.max(
    0,
    availableMonths.indexOf(selectedMonth) === -1
      ? initialMonthIndex
      : availableMonths.indexOf(selectedMonth),
  )
  const visibleMonth = availableMonths[selectedMonthIndex]
  const visibleDays = monthGroups.get(visibleMonth) ?? []
  const monthLabel = visibleMonth
    ? new Date(`${visibleMonth}-01T12:00:00`).toLocaleDateString(undefined, {
        month: 'long',
        year: 'numeric',
      })
    : ''
  const firstWeekday = visibleDays.length
    ? new Date(`${visibleDays[0].date}T12:00:00`).getDay()
    : 0
  return (
    <Card>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <CardTitle className="flex items-center gap-2">
          <Flame size={20} className="text-accent" aria-hidden />
          Study streak
        </CardTitle>
        <span className="text-sm font-semibold tabular-nums text-brand">
          {streak.days}-day streak
        </span>
      </div>
      <p className="mt-1 text-sm text-muted">
        Days with at least one completed plan task.
        {streak.days > 0
          ? streak.active_today
            ? ' Active today.'
            : ' Anchored on the last completed day.'
          : ' Complete a task to start a streak.'}
      </p>
      <section className="mt-5 w-full" aria-label={monthLabel}>
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-bold text-ink">{monthLabel}</h3>
          <div className="flex gap-1">
            <Button
              variant="secondary"
              className="h-9 min-h-9 w-9 rounded-full px-0 py-0"
              aria-label="Previous month"
              disabled={selectedMonthIndex === 0}
              onClick={() => setSelectedMonth(availableMonths[selectedMonthIndex - 1])}
            >
              <ChevronLeft size={17} />
            </Button>
            <Button
              variant="secondary"
              className="h-9 min-h-9 w-9 rounded-full px-0 py-0"
              aria-label="Next month"
              disabled={selectedMonthIndex === availableMonths.length - 1}
              onClick={() => setSelectedMonth(availableMonths[selectedMonthIndex + 1])}
            >
              <ChevronRight size={17} />
            </Button>
          </div>
        </div>
        <div className="mt-3 grid grid-cols-7 gap-1 text-center">
          {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((weekday, index) => (
            <span key={`${weekday}-${index}`} className="rounded border border-line-light bg-surface-secondary py-2 text-[10px] font-bold uppercase text-muted">
              {weekday}
            </span>
          ))}
          {Array.from({ length: firstWeekday }, (_, index) => (
            <span key={`empty-${index}`} className="min-h-16 rounded border border-line-light bg-surface" aria-hidden />
          ))}
          {visibleDays.map((day) => {
                  const { day: dayNum } = dayParts(day.date)
                  const isToday = day.date === today
                  return (
                    <div
                      key={day.date}
                      aria-label={`${day.date}${day.completed ? ', completed' : ''}`}
                      className="flex min-h-16 flex-col items-center rounded border border-line-light bg-surface px-1 pt-2"
                    >
                      <span
                        className={`flex h-8 w-8 items-center justify-center rounded-full border text-xs font-bold tabular-nums ${
                          isToday
                            ? 'border-brand bg-brand text-white'
                            : day.completed
                              ? 'border-good bg-good-soft text-good'
                              : 'border-line-light bg-surface-secondary text-ink'
                        }`}
                      >
                        {dayNum}
                      </span>
                      <div className="mt-1.5 flex h-1.5 justify-center gap-[3px]">
                        {SKILLS.map((skill) => (
                          <span
                            key={skill}
                            aria-hidden
                            className={`h-1.5 w-1.5 rounded-full ${
                              day.skills[skill] ? SKILL_DOT[skill] : 'bg-line'
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                  )
          })}
        </div>
      </section>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
        {SKILLS.map((skill) => (
          <span key={skill} className="flex items-center gap-1.5 text-xs text-muted">
            <span aria-hidden className={`h-2 w-2 rounded-full ${SKILL_DOT[skill]}`} />
            {SKILL_LABEL[skill]}
          </span>
        ))}
      </div>
    </Card>
  )
}

/** Inline, auto-saving plan name; persists on blur/Enter. */
function PlanNameInput({
  plan,
  onSaved,
}: {
  plan: StudyPlan
  onSaved: (plan: StudyPlan) => void
}) {
  const [value, setValue] = useState(plan.name)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')

  useEffect(() => setValue(plan.name), [plan.name])

  async function persist() {
    const next = value.trim()
    if (next === plan.name) return
    setSaving(true)
    setSaveError('')
    try {
      onSaved(await api.patch<StudyPlan>('/me/study-plan/', { name: next }))
    } catch (reason) {
      setSaveError(
        reason instanceof Error ? reason.message : 'Could not save the plan name.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-w-0">
      <label htmlFor="plan-name" className="text-xs font-semibold uppercase tracking-wider text-muted">
        Plan name
      </label>
      <input
        id="plan-name"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onBlur={() => void persist()}
        onKeyDown={(event) => {
          if (event.key === 'Enter') event.currentTarget.blur()
        }}
        placeholder="Study Plan"
        maxLength={120}
        disabled={saving}
        aria-describedby={saveError ? 'plan-name-error' : undefined}
        className="mt-1 w-full min-w-0 rounded-input border border-line bg-surface px-3 py-2 text-sm font-semibold text-ink placeholder:text-muted focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand disabled:opacity-60 sm:w-64"
      />
      {saveError && (
        <p id="plan-name-error" role="alert" className="mt-1 text-xs text-bad">
          {saveError}
        </p>
      )}
    </div>
  )
}

export function StudyPlanPage() {
  const { status } = useAuth()
  const [plan, setPlan] = useState<StudyPlan | null>(null)
  const [error, setError] = useState('')
  const [regenerating, setRegenerating] = useState(false)

  useEffect(() => {
    if (status !== 'authenticated') {
      setPlan(null)
      return
    }
    api
      .get<StudyPlan>('/me/study-plan/')
      .then(setPlan)
      .catch((reason: unknown) => {
        setError(
          reason instanceof Error ? reason.message : 'Could not load your plan.',
        )
      })
  }, [status])

  const groups = useMemo(() => {
    const result = new Map<string, StudyTask[]>()
    for (const task of plan?.tasks ?? []) {
      result.set(task.scheduled_date, [...(result.get(task.scheduled_date) ?? []), task])
    }
    return [...result.entries()]
  }, [plan])

  async function setState(task: StudyTask, state: StudyTask['state']) {
    try {
      await api.patch(`/me/study-plan/tasks/${task.id}/`, { state })
      // Refetch so the streak bar and day strip reflect the new completion.
      setPlan(await api.get<StudyPlan>('/me/study-plan/'))
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : 'Could not update the task.',
      )
    }
  }

  async function regenerate() {
    setRegenerating(true)
    try {
      setPlan(await api.post<StudyPlan>('/me/study-plan/'))
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : 'Could not rebuild the plan.',
      )
    } finally {
      setRegenerating(false)
    }
  }

  if (status === 'loading') {
    return <p role="status" className="py-16 text-center text-muted">Loading study plan…</p>
  }
  if (status !== 'authenticated') {
    return <AccountRequired title="Study Plan" />
  }

  return (
    <div className="mx-auto w-full max-w-[1600px] space-y-6 animate-fade-up">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Explainable daily actions</p>
          <h1 className="mt-1 text-3xl font-bold text-ink">Study Plan</h1>
          <p className="mt-2 max-w-3xl text-muted">
            Your schedule follows your preferred days and minutes. Weaker or
            unpractised skills come first without starving stronger skills.
          </p>
        </div>
        <Button variant="secondary" disabled={regenerating} onClick={() => void regenerate()}>
          <RefreshCcw className={regenerating ? 'animate-spin' : ''} size={17} />
          Rebuild plan
        </Button>
      </header>

      {error && <p role="alert" className="rounded-input bg-bad-soft p-3 text-bad">{error}</p>}

      {!plan ? (
        <p role="status" className="py-10 text-center text-muted">
          Generating your first plan…
        </p>
      ) : (
        <>
          <Card className="p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0">
                <h2 className="flex items-center gap-2 text-xl font-bold text-ink">
                  <CalendarRange size={21} aria-hidden />
                  {plan.name ? plan.name : `Study Plan v${plan.version}`}
                </h2>
                <p className="mt-2 text-sm text-muted">{plan.reason_summary.rule}</p>
                <p className="mt-1 text-xs text-muted">
                  Based on {plan.reason_summary.source_attempts} completed attempt(s).
                  Every recommendation displays its reason.
                </p>
              </div>
              <PlanNameInput plan={plan} onSaved={setPlan} />
            </div>
          </Card>

          <StreakBar plan={plan} />

          <div className="space-y-6">
            {groups.map(([date, tasks]) => (
              <section key={date}>
                <h2 className="text-xl font-bold text-ink">
                  {new Date(`${date}T12:00:00`).toLocaleDateString(undefined, {
                    weekday: 'long',
                    month: 'long',
                    day: 'numeric',
                  })}
                </h2>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  {tasks.map((task) => (
                    <Card
                      key={task.id}
                      className={`p-5 ${task.state === 'completed' ? 'border-good/30 bg-good-soft/30' : ''}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-bold uppercase tracking-wider text-accent">
                            {SKILL_LABEL[task.skill]} · {task.minutes} min
                          </p>
                          <h3 className="mt-1 font-bold text-ink">{task.title}</h3>
                        </div>
                        {task.state === 'completed' && (
                          <CheckCircle2 className="text-good" size={22} aria-label="Completed" />
                        )}
                      </div>
                      <p className="mt-3 text-sm leading-6 text-muted">{task.reason}</p>
                      <div className="mt-4 flex flex-wrap gap-2">
                        <Link className="btn-primary" to={task.destination}>
                          Open practice
                        </Link>
                        <Button
                          variant="secondary"
                          onClick={() =>
                            void setState(task, task.state === 'completed' ? 'pending' : 'completed')
                          }
                        >
                          {task.state === 'completed' ? 'Undo' : 'Mark complete'}
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
