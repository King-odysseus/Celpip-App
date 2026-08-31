import { CalendarDays, CheckCircle2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, CardTitle } from '../../components/ui'
import type { StudyTask } from '../learning/types'
import { StudyTaskLaunch } from '../learning/StudyTaskLaunch'
import { SKILL_LABELS } from './labels'

function formatDay(isoDate: string): string {
  return new Date(`${isoDate}T12:00:00`).toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  })
}

/** Today's scheduled tasks, or the next upcoming task when today is empty. */
export function TodayTasks({
  date,
  tasks,
  nextUpcoming,
}: {
  date: string
  tasks: StudyTask[]
  nextUpcoming: StudyTask | null
}) {
  return (
    <Card>
      <div className="flex items-start gap-3">
        <CalendarDays size={22} className="mt-0.5 shrink-0 text-accent" aria-hidden />
        <div className="min-w-0 flex-1">
          <CardTitle className="mb-3">Today&rsquo;s study</CardTitle>
          <p className="mb-3 text-sm text-muted">
            {formatDay(date)}
          </p>

          {tasks.length > 0 ? (
            <ul className="space-y-3">
              {tasks.map((task) => (
                <li
                  key={task.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line p-3"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-ink">{task.title}</p>
                    <p className="text-xs text-muted">
                      {SKILL_LABELS[task.skill]} · {task.minutes} min
                    </p>
                    {task.previously_completed && task.state !== 'completed' && (
                      <span className="mt-1 inline-flex rounded-full bg-good-soft px-2 py-0.5 text-[11px] font-semibold text-good">
                        Previously completed
                      </span>
                    )}
                  </div>
                  {task.state === 'completed' ? (
                    <span className="inline-flex items-center gap-1 text-sm font-semibold text-good">
                      <CheckCircle2 size={16} aria-hidden /> Done
                    </span>
                  ) : (
                    <StudyTaskLaunch task={task} label="Open" />
                  )}
                </li>
              ))}
            </ul>
          ) : nextUpcoming ? (
            <div className="rounded-lg border border-line p-3">
              <p className="text-sm text-muted">Nothing scheduled today.</p>
              <p className="mt-1 text-sm text-ink">
                Next up: {nextUpcoming.title} on {formatDay(nextUpcoming.scheduled_date)}.
              </p>
              <div className="mt-3"><StudyTaskLaunch task={nextUpcoming} label="Open next task" /></div>
            </div>
          ) : (
            <p className="text-sm text-muted">
              No study plan yet.{' '}
              <Link to="/study-plan" className="font-semibold text-brand hover:underline">
                Build your plan
              </Link>{' '}
              to get daily tasks.
            </p>
          )}
        </div>
      </div>
    </Card>
  )
}
