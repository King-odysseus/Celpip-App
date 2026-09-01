import { ArrowRight, Compass } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, CardTitle } from '../../components/ui'
import type { Dashboard, Skill } from '../learning/types'
import { StudyTaskLaunch } from '../learning/StudyTaskLaunch'
import { SKILL_LABELS } from './labels'

function practicePath(skill: Skill): string {
  return skill === 'reading' ? '/practice' : `/practice/${skill}`
}

/** Turns the dashboard into a single clear next action for returning learners. */
export function NextBestSession({ dashboard }: { dashboard: Dashboard }) {
  const task = dashboard.today.tasks.find((item) => item.state !== 'completed') ?? dashboard.next_upcoming_task
  const attention = dashboard.signals.needs_attention

  if (!task) {
    if (!attention) {
    return (
      <Card className="border-brand/30 bg-gradient-to-br from-brand-soft/50 to-surface">
        <div className="flex items-start gap-3">
          <Compass size={22} className="mt-0.5 shrink-0 text-accent" aria-hidden />
          <div>
            <CardTitle>Set your starting point</CardTitle>
            <p className="mt-1 text-sm leading-6 text-muted">
              Complete a short practice set in any skill to create your first evidence-based recommendation.
            </p>
            <Link to="/practice" className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-brand hover:underline">
              Explore practice <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </Card>
    )
    }
    return (
      <Card className="border-brand/30 bg-gradient-to-br from-brand-soft/50 to-surface">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <Compass size={22} className="mt-0.5 shrink-0 text-accent" aria-hidden />
            <div>
              <p className="eyebrow">Recommended next</p>
              <CardTitle className="mt-1">Practise {SKILL_LABELS[attention.skill]}</CardTitle>
              <p className="mt-1 text-sm leading-6 text-muted">{attention.basis}. Build evidence in this skill before your next mock.</p>
            </div>
          </div>
          <Link to={practicePath(attention.skill)} className="inline-flex min-h-11 items-center gap-2 rounded-full bg-brand px-4 py-2 text-sm font-semibold text-white hover:opacity-90">
            Start practice <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </div>
      </Card>
    )
  }

  return (
    <Card className="border-brand/30 bg-gradient-to-br from-brand-soft/50 to-surface">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <Compass size={22} className="mt-0.5 shrink-0 text-accent" aria-hidden />
          <div>
            <p className="eyebrow">Recommended next</p>
            <CardTitle className="mt-1">Continue with {task.title}</CardTitle>
            <p className="mt-1 text-sm leading-6 text-muted">
              {SKILL_LABELS[task.skill]} · {task.minutes} minutes · {task.reason}
            </p>
          </div>
        </div>
        <StudyTaskLaunch task={task} label="Start session" />
      </div>
    </Card>
  )
}
