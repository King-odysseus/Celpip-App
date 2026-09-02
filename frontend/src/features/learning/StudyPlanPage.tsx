import {
  CalendarRange,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Flame,
  RefreshCcw,
  Timer,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Button, ButtonLink, Card, CardTitle } from '../../components/ui'
import { api } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'
import { AccountRequired } from './ProgressPage'
import type { Skill, StudyPlan, StudyTask } from './types'
import { StudyTaskLaunch } from './StudyTaskLaunch'

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

const MOCK_WEEKDAYS = [
  { iso: 6, label: 'Sat' },
  { iso: 7, label: 'Sun' },
]

const DIFFICULTY_LABEL: Record<number, string> = {
  1: 'Foundation',
  2: 'Developing',
  3: 'Challenge',
}

function taskDifficulty(task: StudyTask): number | null {
  try {
    const value = Number(new URL(task.destination, window.location.origin).searchParams.get('difficulty'))
    return value >= 1 && value <= 3 ? value : null
  } catch {
    return null
  }
}

function dayParts(date: string): { day: string } {
  const value = new Date(`${date}T12:00:00`)
  return {
    day: value.toLocaleDateString(undefined, { day: 'numeric' }),
  }
}

/**
 * A task can be opened and finished from any day it's shown on — catch-up
 * work stays reachable from its original scheduled date so nothing missed
 * is ever hidden. Completing it always credits the real day it happened
 * (streak/calendar accounting already uses `completed_at`, never
 * `scheduled_date`), so the card says so explicitly whenever that differs
 * from the section it's filed under — otherwise a bare checkmark under an
 * old date reads as if that old day were retroactively credited.
 */
function completionDateLabel(completedAtIso: string, scheduledDate: string): string | null {
  const completedDate = new Date(completedAtIso)
  // Build the local-calendar-date string by hand: `.toISOString()` converts
  // to UTC first, which silently shifts the date by a day for any timezone
  // east of UTC (e.g. midnight local on the 29th is still the 28th in UTC).
  const year = completedDate.getFullYear()
  const month = String(completedDate.getMonth() + 1).padStart(2, '0')
  const day = String(completedDate.getDate()).padStart(2, '0')
  const completedLocalDate = `${year}-${month}-${day}`
  if (completedLocalDate === scheduledDate) return null
  return `Completed ${completedDate.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}, not on the originally scheduled day.`
}

/** Calendar showing which skills were completed on each day + the streak. */
function StreakBar({
  plan,
  selectedDate,
  onSelectDate,
}: {
  plan: StudyPlan
  selectedDate: string | null
  onSelectDate: (date: string) => void
}) {
  const { streak, days } = plan.consistency
  // Older cached plan payloads may not include the consistency strip's
  // `today` field; use the latest supplied day so the page remains usable.
  const today = plan.consistency.today ?? days.at(-1)?.date ?? new Date().toISOString().slice(0, 10)
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
  const mockDates = new Set((plan.mock_checkpoints ?? []).map((checkpoint) => checkpoint.date))
  const tasksByDate = new Map<string, StudyTask[]>()
  for (const task of plan.tasks) {
    tasksByDate.set(task.scheduled_date, [
      ...(tasksByDate.get(task.scheduled_date) ?? []),
      task,
    ])
  }
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
              className="h-9 min-h-9 w-9 rounded-full !px-0 !py-0"
              aria-label="Previous month"
              disabled={selectedMonthIndex === 0}
              onClick={() => setSelectedMonth(availableMonths[selectedMonthIndex - 1])}
            >
              <ChevronLeft size={17} />
            </Button>
            <Button
              variant="secondary"
              className="h-9 min-h-9 w-9 rounded-full !px-0 !py-0"
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
                  const dayTasks = tasksByDate.get(day.date) ?? []
                  const hasMissedTasks = dayTasks.some(
                    (task) => task.state === 'pending' && day.date < today,
                  )
                  return (
                    <button
                      type="button"
                      key={day.date}
                      aria-label={`${day.date}${day.completed ? ', completed' : ''}${hasMissedTasks ? ', missed tasks' : ''}, view scheduled work`}
                      aria-pressed={selectedDate === day.date}
                      onClick={() => onSelectDate(day.date)}
                      title="View scheduled work for this day"
                      className={`flex min-h-16 cursor-pointer flex-col items-center rounded border bg-surface px-1 pt-2 transition hover:border-brand focus-visible:outline-2 focus-visible:outline-brand ${selectedDate === day.date ? 'border-brand ring-2 ring-brand/20' : 'border-line-light'}`}
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
                      {mockDates.has(day.date) && (
                        <span className="mt-1 flex items-center gap-0.5 text-[9px] font-bold uppercase text-accent">
                          <Timer size={10} aria-hidden /> Mock
                        </span>
                      )}
                    </button>
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
    <div className="min-w-0 w-full">
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
        className="mt-1 min-h-10 w-full min-w-0 rounded-input border border-line bg-surface px-3 py-2 text-sm font-semibold text-ink placeholder:text-muted focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand disabled:opacity-60"
      />
      {saveError && (
        <p id="plan-name-error" role="alert" className="mt-1 text-xs text-bad">
          {saveError}
        </p>
      )}
    </div>
  )
}

function MockIntervalInput({ plan, onSaved }: { plan: StudyPlan; onSaved: (plan: StudyPlan) => void }) {
  const [value, setValue] = useState(String(plan.reason_summary.mock_interval_days ?? 7))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const active = (plan.reason_summary.mock_schedule_mode ?? 'interval') === 'interval'

  useEffect(() => setValue(String(plan.reason_summary.mock_interval_days ?? 7)), [plan.reason_summary.mock_interval_days])

  async function persist() {
    const days = Number(value)
    if (!Number.isInteger(days) || days < 1 || days > 30) {
      setError('Choose an interval from 1 to 30 days.')
      return
    }
    setSaving(true)
    setError('')
    try {
      onSaved(await api.patch<StudyPlan>('/me/study-plan/', { mock_interval_days: days }))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not save the mock interval.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-w-0 w-full">
      <label htmlFor="mock-interval" className="text-xs font-semibold uppercase tracking-wider text-muted">
        Mock/review interval
      </label>
      <div className={`mt-1 flex items-center gap-2 ${active ? '' : 'opacity-50'}`}>
        <input
          id="mock-interval"
          type="number"
          min={1}
          max={30}
          value={value}
          disabled={saving || !active}
          onChange={(event) => setValue(event.target.value)}
          onBlur={() => void persist()}
          onKeyDown={(event) => {
            if (event.key === 'Enter') event.currentTarget.blur()
          }}
          className="min-h-10 w-24 rounded-input border border-line bg-surface px-3 py-2 text-sm font-semibold text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand disabled:opacity-60"
        />
        <span className="text-sm text-muted">days</span>
      </div>
      {error && <p role="alert" className="mt-1 text-xs text-bad">{error}</p>}
    </div>
  )
}

function MockScheduleModeInput({ plan, onSaved }: { plan: StudyPlan; onSaved: (plan: StudyPlan) => void }) {
  const mode = plan.reason_summary.mock_schedule_mode ?? 'interval'
  const [saving, setSaving] = useState(false)
  async function choose(next: 'interval' | 'weekdays') {
    if (next === mode) return
    setSaving(true)
    try { onSaved(await api.patch<StudyPlan>('/me/study-plan/', { mock_schedule_mode: next })) }
    finally { setSaving(false) }
  }
  return (
    <fieldset className="min-w-0 w-full sm:col-span-2 lg:col-span-1">
      <legend className="text-xs font-semibold uppercase tracking-wider text-muted">Mock schedule</legend>
      <div className="mt-1 grid gap-2">
        {(['interval', 'weekdays'] as const).map((value) => (
          <label key={value} className="flex min-h-10 cursor-pointer items-center gap-2 rounded-input border border-line bg-surface px-3 py-2 text-sm font-semibold text-ink">
            <input type="radio" name="mock-schedule-mode" value={value} checked={mode === value} disabled={saving} onChange={() => void choose(value)} className="h-4 w-4 accent-brand" />
            {value === 'interval' ? 'Every X days' : 'Specific days'}
          </label>
        ))}
      </div>
      <p className="mt-1 text-xs text-muted">Choose one scheduling method.</p>
    </fieldset>
  )
}

function MockDaysInput({ plan, onSaved }: { plan: StudyPlan; onSaved: (plan: StudyPlan) => void }) {
  const selected = plan.reason_summary.mock_weekdays ?? [6, 7]
  const enabled = (plan.reason_summary.mock_schedule_mode ?? 'interval') === 'weekdays'
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function toggle(day: number) {
    const next = selected.includes(day) ? selected.filter((value) => value !== day) : [...selected, day].sort()
    if (!next.length) {
      setError('Choose at least one mock-test day.')
      return
    }
    setSaving(true)
    setError('')
    try {
      onSaved(await api.patch<StudyPlan>('/me/study-plan/', { mock_weekdays: next }))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not save mock-test days.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <fieldset className="min-w-0 w-full">
      <legend className="text-xs font-semibold uppercase tracking-wider text-muted">Mock-test days</legend>
      <div className="mt-1 flex gap-2">
        {MOCK_WEEKDAYS.map((day) => {
          const active = selected.includes(day.iso)
          return (
            <button key={day.iso} type="button" aria-pressed={active} disabled={saving || !enabled} onClick={() => void toggle(day.iso)} className={`min-h-10 rounded-input border px-3 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-brand ${active ? 'border-brand bg-brand-soft text-brand' : 'border-line text-muted hover:border-brand'} ${!enabled ? 'opacity-50' : ''}`}>
              {day.label}
            </button>
          )
        })}
      </div>
      <p className="mt-1 text-xs text-muted">Active only with Specific days.</p>
      {error && <p role="alert" className="mt-1 text-xs text-bad">{error}</p>}
    </fieldset>
  )
}

function DifficultyInput({ plan, onSaved }: { plan: StudyPlan; onSaved: (plan: StudyPlan) => void }) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function persist(value: NonNullable<StudyPlan['difficulty_preference']>) {
    setSaving(true)
    setError('')
    try {
      onSaved(await api.patch<StudyPlan>('/me/study-plan/', { difficulty_preference: value }))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not update lesson difficulty.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-w-0 w-full sm:col-span-2 lg:col-span-1">
      <label htmlFor="plan-difficulty" className="text-xs font-semibold uppercase tracking-wider text-muted">
        Lesson difficulty
      </label>
      <select
        id="plan-difficulty"
        value={plan.difficulty_preference ?? 'adaptive'}
        disabled={saving}
        onChange={(event) => void persist(event.target.value as NonNullable<StudyPlan['difficulty_preference']>)}
        className="mt-1 min-h-10 w-full rounded-input border border-line bg-surface px-3 py-2 text-sm font-semibold text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand disabled:opacity-60"
      >
        <option value="adaptive">AI-assisted adaptive · graduates over time</option>
        <option value="foundation">Foundation · level 1</option>
        <option value="developing">Developing · level 2</option>
        <option value="challenge">Challenge · level 3</option>
      </select>
      <p className="mt-1 text-xs text-muted">
        Adaptive uses your target, objective results, and AI-assisted Writing/Speaking estimates, then increases every three study days.
      </p>
      {plan.reason_summary.difficulty_by_skill && (
        <div className="mt-2 flex max-w-sm flex-wrap gap-1.5" aria-label="Starting difficulty by skill">
          {SKILLS.map((skill) => (
            <span key={skill} className="rounded-full bg-brand-soft px-2 py-1 text-[11px] font-semibold text-brand">
              {SKILL_LABEL[skill]}: {DIFFICULTY_LABEL[plan.reason_summary.difficulty_by_skill?.[skill] ?? 1]}
            </span>
          ))}
        </div>
      )}
      {error && <p role="alert" className="mt-1 text-xs text-bad">{error}</p>}
    </div>
  )
}

export function StudyPlanPage() {
  const { status } = useAuth()
  const [plan, setPlan] = useState<StudyPlan | null>(null)
  const [error, setError] = useState('')
  const [regenerating, setRegenerating] = useState(false)
  const [confirmingTaskId, setConfirmingTaskId] = useState<number | null>(null)
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [showAllTasks, setShowAllTasks] = useState(false)

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
    const result = new Map<string, { tasks: StudyTask[]; mocks: NonNullable<StudyPlan['mock_checkpoints']> }>()
    for (const task of plan?.tasks ?? []) {
      const group = result.get(task.scheduled_date) ?? { tasks: [], mocks: [] }
      result.set(task.scheduled_date, { ...group, tasks: [...group.tasks, task] })
    }
    for (const checkpoint of plan?.mock_checkpoints ?? []) {
      const group = result.get(checkpoint.date) ?? { tasks: [], mocks: [] }
      result.set(checkpoint.date, { ...group, mocks: [...group.mocks, checkpoint] })
    }
    return [...result.entries()].sort(([left], [right]) => left.localeCompare(right))
  }, [plan])

  const visibleGroups = useMemo(() => {
    if (!plan) return []
    if (showAllTasks) return groups
    if (selectedDate) return groups.filter(([date]) => date === selectedDate)
    // Same fallback as StreakBar: an older/cached plan payload can omit
    // `consistency.today` entirely. Without a fallback, `today` is
    // `undefined`, `date === today` never matches, and every task silently
    // disappears from the default view instead of showing today's work.
    const today = plan.consistency.today ?? groups.at(-1)?.[0] ?? new Date().toISOString().slice(0, 10)
    const missedDates = new Set(
      groups
        .filter(([date, day]) =>
          date < today && day.tasks.some((task) => task.state === 'pending'),
        )
        .map(([date]) => date),
    )
    return groups.filter(([date]) => date === today || missedDates.has(date))
  }, [groups, plan, selectedDate, showAllTasks])

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
          {plan.overdue_tasks?.length ? (
            <Card className="border-warn/40 bg-warn-soft" role="alert">
              <h2 className="font-bold text-ink">
                You missed {plan.overdue_tasks.length === 1 ? 'a study task' : `${plan.overdue_tasks.length} study tasks`}
              </h2>
              <p className="mt-1 text-sm text-muted">
                These tasks are still pending and were not marked complete automatically. Finish them when you can, then confirm completion.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {plan.overdue_tasks.slice(0, 3).map((task) => (
                  <StudyTaskLaunch key={task.id} task={task} label={`Open ${SKILL_LABEL[task.skill]}`} />
                ))}
              </div>
            </Card>
          ) : null}
          <Card>
            <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
              <h2 className="flex min-w-0 items-center gap-2 text-xl font-bold text-ink">
                <CalendarRange size={21} className="shrink-0 text-accent" aria-hidden />
                <span className="truncate">
                  {plan.name ? plan.name : `Study Plan v${plan.version}`}
                </span>
              </h2>
              <span className="shrink-0 rounded-full bg-brand-soft px-3 py-1 text-xs font-semibold text-brand">
                Mock every {plan.reason_summary.mock_interval_days ?? 7} days
              </span>
            </div>
            <p className="mt-2 max-w-prose text-sm leading-6 text-muted">
              {plan.reason_summary.rule}
            </p>
            <p className="mt-1 max-w-prose text-xs leading-5 text-muted">
              Based on {plan.reason_summary.source_attempts} completed attempt(s).
              Every recommendation displays its reason.
            </p>

            {/* The editable controls sit in their own panel so they read as a
                group of settings rather than trailing off the prose above. */}
            <div className="mt-5 rounded-card border border-line bg-surface-secondary/50 p-4">
              <h3 className="eyebrow">Plan settings</h3>
              <div className="mt-3 grid items-start gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <PlanNameInput plan={plan} onSaved={setPlan} />
                <DifficultyInput plan={plan} onSaved={setPlan} />
                <MockScheduleModeInput plan={plan} onSaved={setPlan} />
                <MockIntervalInput plan={plan} onSaved={setPlan} />
                <MockDaysInput plan={plan} onSaved={setPlan} />
                <MockDaysInput plan={plan} onSaved={setPlan} />
              </div>
            </div>
          </Card>

          <StreakBar
            plan={plan}
            selectedDate={selectedDate}
            onSelectDate={(date) => {
              setSelectedDate(date)
              setShowAllTasks(false)
            }}
          />

          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted">
                {selectedDate
                  ? `Showing the schedule for ${new Date(`${selectedDate}T12:00:00`).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}.`
                  : showAllTasks
                    ? 'Showing every scheduled lesson and test.'
                    : 'Today and missed lessons are shown. Click a calendar day to view its schedule.'}
              </p>
              <Button
                variant="secondary"
                onClick={() => {
                  setShowAllTasks((current) => !current)
                  setSelectedDate(null)
                }}
              >
                {showAllTasks ? 'Collapse all scheduled work' : 'View all scheduled work'}
              </Button>
            </div>
            {visibleGroups.map(([date, day]) => (
              <section key={date}>
                <h2 className="text-xl font-bold text-ink">
                  {new Date(`${date}T12:00:00`).toLocaleDateString(undefined, {
                    weekday: 'long',
                    month: 'long',
                    day: 'numeric',
                  })}
                </h2>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  {day.mocks.map((checkpoint) => (
                    <Card key={`mock-${checkpoint.date}`} className="border-accent/40 bg-accent-soft/20 p-5">
                      <div className="flex items-start gap-3">
                        <span className="rounded-full bg-accent-fill p-2 text-white"><Timer size={19} aria-hidden /></span>
                        <div>
                          <p className="text-xs font-bold uppercase tracking-wider text-accent">Mock-test day</p>
                          <h3 className="mt-1 font-bold text-ink">{checkpoint.title}</h3>
                        </div>
                      </div>
                      <p className="mt-3 text-sm leading-6 text-muted">{checkpoint.reason}</p>
                      <ButtonLink to={checkpoint.destination} className="mt-4">Open mock tests</ButtonLink>
                    </Card>
                  ))}
                  {day.tasks.map((task) => (
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
                          <div className="mt-2 flex flex-wrap gap-2">
                            {taskDifficulty(task) && (
                              <span className="inline-flex rounded-full bg-info-bg px-2.5 py-1 text-xs font-semibold text-info">
                                {DIFFICULTY_LABEL[taskDifficulty(task) ?? 1]} difficulty
                              </span>
                            )}
                            {task.previously_completed && task.state !== 'completed' && (
                              <span className="inline-flex items-center rounded-full bg-good-soft px-2.5 py-1 text-xs font-semibold text-good">
                                Previously completed
                              </span>
                            )}
                          </div>
                        </div>
                        {task.state === 'completed' && (
                          <CheckCircle2 className="text-good" size={22} aria-label="Completed" />
                        )}
                      </div>
                      {task.state === 'completed' && task.completed_at && (
                        <p className="mt-1 text-xs font-semibold text-good">
                          {completionDateLabel(task.completed_at, date)}
                        </p>
                      )}
                      <p className="mt-3 text-sm leading-6 text-muted">{task.reason}</p>
                      <div className="mt-4 flex flex-wrap gap-2">
                        <StudyTaskLaunch task={task} />
                        <Button
                          variant="secondary"
                          onClick={() => {
                            if (task.state === 'completed') {
                              void setState(task, 'pending')
                            } else {
                              setConfirmingTaskId(task.id)
                            }
                          }}
                        >
                          {task.state === 'completed' ? 'Undo' : 'Mark complete'}
                        </Button>
                      </div>
                      {confirmingTaskId === task.id && task.state !== 'completed' && (
                        <div className="mt-4 rounded-input border border-brand/30 bg-brand-soft p-4" role="dialog" aria-label="Confirm lesson understanding">
                          <p className="text-sm font-semibold text-ink">Do you understand this lesson?</p>
                          <p className="mt-1 text-xs text-muted">Confirm after you have completed the recommended practice.</p>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <Button
                              variant="primary"
                              onClick={() => {
                                setConfirmingTaskId(null)
                                void setState(task, 'completed')
                              }}
                            >
                              Yes, I understand
                            </Button>
                            <Button variant="ghost" onClick={() => setConfirmingTaskId(null)}>
                              Not yet
                            </Button>
                          </div>
                        </div>
                      )}
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
