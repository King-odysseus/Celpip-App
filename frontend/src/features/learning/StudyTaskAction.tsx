import { CheckCircle2, Flame, PartyPopper } from 'lucide-react'
import { useState } from 'react'
import { ButtonLink, Button } from '../../components/ui'
import { api } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'
import type { StudyPlan, StudyTask } from './types'

type CompletionOutcome =
  | { kind: 'more_today'; next: StudyTask }
  | { kind: 'day_complete'; streakDays: number }

export function StudyTaskAction({ taskId }: { taskId: string | null }) {
  const { status } = useAuth()
  const [completed, setCompleted] = useState(false)
  const [outcome, setOutcome] = useState<CompletionOutcome | null>(null)
  const [confirming, setConfirming] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  if (status !== 'authenticated' || !taskId) return null

  async function markComplete() {
    setSaving(true)
    setError('')
    try {
      await api.patch(`/me/study-plan/tasks/${taskId}/`, { state: 'completed' })
      // Refetch the plan to find this task's scheduled day and whether any
      // other lesson for that same day is still pending — that decides
      // whether to offer the next lesson or celebrate the day as done.
      const plan = await api.get<StudyPlan>('/me/study-plan/')
      const thisTask = plan.tasks.find((task) => String(task.id) === taskId)
      const scheduledDate = thisTask?.scheduled_date
      const remainingToday = scheduledDate
        ? plan.tasks
            .filter((task) => task.scheduled_date === scheduledDate && task.state === 'pending')
            .sort((left, right) => left.order - right.order || left.id - right.id)
        : []
      setOutcome(
        remainingToday.length > 0
          ? { kind: 'more_today', next: remainingToday[0] }
          : { kind: 'day_complete', streakDays: plan.consistency.streak.days },
      )
      setCompleted(true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not mark the study task complete.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-input border border-brand/30 bg-brand-soft p-4">
      {completed ? (
        <CompletionOutcomeView outcome={outcome} />
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm font-semibold text-ink">This lesson is in your Study Plan.</p>
            <Button variant="secondary" disabled={saving} onClick={() => setConfirming(true)}>
              Mark as complete
            </Button>
          </div>
          {confirming && (
            <div className="mt-3 rounded-input border border-brand/30 bg-surface p-3" role="dialog" aria-label="Confirm lesson understanding">
              <p className="text-sm font-semibold text-ink">Do you understand this lesson?</p>
              <p className="mt-1 text-xs text-muted">Confirm only after completing the recommended practice.</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button disabled={saving} onClick={() => void markComplete()}>
                  {saving ? 'Saving…' : 'Yes, I understand'}
                </Button>
                <Button variant="ghost" disabled={saving} onClick={() => setConfirming(false)}>Not yet</Button>
              </div>
            </div>
          )}
        </>
      )}
      {error && <p role="alert" className="mt-2 text-xs text-bad">{error}</p>}
    </div>
  )
}

function CompletionOutcomeView({ outcome }: { outcome: CompletionOutcome | null }) {
  if (!outcome) {
    // The completion patch itself succeeded even though the follow-up plan
    // refetch failed — still confirm completion rather than showing nothing.
    return (
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="flex items-center gap-2 text-sm font-semibold text-good">
          <CheckCircle2 size={18} /> Study Plan task completed
        </p>
        <ButtonLink to="/study-plan" variant="secondary">Return to Study Plan</ButtonLink>
      </div>
    )
  }

  if (outcome.kind === 'more_today') {
    return (
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="flex items-center gap-2 text-sm font-semibold text-good">
            <CheckCircle2 size={18} /> Lesson complete
          </p>
          <p className="mt-2 text-xs font-bold uppercase tracking-wider text-muted">Next in today&rsquo;s Study Plan</p>
          <p className="mt-1 font-bold text-ink">{outcome.next.title}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <ButtonLink to={outcome.next.destination}>Next question</ButtonLink>
          <ButtonLink to="/study-plan" variant="secondary">Study Plan</ButtonLink>
        </div>
      </div>
    )
  }

  return (
    <div className="animate-scale-in text-center">
      <p className="flex items-center justify-center gap-2 text-lg font-bold text-good">
        <PartyPopper size={22} /> Today's study plan is complete!
      </p>
      <p className="mt-1 flex items-center justify-center gap-1.5 text-sm font-semibold text-brand">
        <Flame size={16} /> {outcome.streakDays}-day streak
      </p>
      <ButtonLink to="/study-plan" className="mt-4">Return to Study Plan</ButtonLink>
    </div>
  )
}
