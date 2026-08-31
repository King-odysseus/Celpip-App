import { ArrowRight, CheckCircle2, Lightbulb, X } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../../components/ui'
import { api } from '../../lib/api'
import type { Mistake, Progress, StudyTask } from './types'

type CoachingData = { progress: Progress; mistakes: Mistake[] }

let coachingRequest: Promise<CoachingData> | null = null

function loadCoaching(): Promise<CoachingData> {
  coachingRequest ??= Promise.all([
    api.get<Progress>('/me/progress/'),
    api.get<{ results: Mistake[] }>('/me/mistakes/'),
  ]).then(([progress, mistakes]) => ({ progress, mistakes: mistakes.results }))
  return coachingRequest
}

function tipsFor(task: StudyTask, data: CoachingData): string[] {
  const tips: string[] = []
  const skill = data.progress.skills.find((item) => item.skill === task.skill)
  const taskType = data.progress.task_types.find((item) => item.task_type === task.task_type)
  const target = data.progress.target_guidance?.find((item) => item.skill === task.skill)

  if (skill?.accuracy_percent !== null && skill?.accuracy_percent !== undefined) {
    tips.push(
      skill.accuracy_percent < 70
        ? `${task.skill[0].toUpperCase()}${task.skill.slice(1)} accuracy is ${skill.accuracy_percent}%. Slow down and prove each answer from the prompt.`
        : `Your ${task.skill} accuracy is ${skill.accuracy_percent}%. Keep that standard while working on this lesson.`,
    )
  } else {
    tips.push(`This lesson will establish a stronger ${task.skill} baseline. Notice which question types take you longest.`)
  }

  if (taskType && taskType.total > 0 && taskType.accuracy_percent < 75) {
    tips.push(`${task.title} is at ${taskType.accuracy_percent}% accuracy. Review why each incorrect option is wrong before moving on.`)
  }

  data.mistakes
    .filter((mistake) => mistake.skill === task.skill && mistake.state === 'open')
    .sort((a, b) => b.occurrences - a.occurrences)
    .slice(0, 2)
    .forEach((mistake) => tips.push(`Review this recurring pattern: “${mistake.explanation}”`))

  if (target?.attained === false && target.tips[0]) tips.push(target.tips[0])
  if (tips.length === 0) tips.push(task.reason)
  return tips.slice(0, 4)
}

export function StudyTaskLaunch({
  task,
  label = 'Open practice',
}: {
  task: StudyTask
  label?: string
}) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [tips, setTips] = useState<string[]>([])

  async function begin() {
    setOpen(true)
    setLoading(true)
    setError('')
    try {
      const data = await loadCoaching()
      setTips(tipsFor(task, data))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Your recap could not be loaded.')
      setTips([task.reason])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Button className="text-sm" onClick={() => void begin()}>
        {label} <ArrowRight size={16} />
      </Button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="presentation">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby={`recap-title-${task.id}`}
            className="w-full max-w-xl rounded-card border border-line bg-surface p-6 shadow-elevated"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="eyebrow">Before you begin</p>
                <h2 id={`recap-title-${task.id}`} className="mt-1 text-2xl font-bold text-ink">
                  Your improvement recap
                </h2>
                <p className="mt-2 text-sm text-muted">Use these tips during today&rsquo;s {task.skill} lesson.</p>
              </div>
              <button type="button" aria-label="Close recap" onClick={() => setOpen(false)} className="rounded-full p-2 text-muted hover:bg-surface-secondary hover:text-ink">
                <X size={20} />
              </button>
            </div>

            {loading ? (
              <p role="status" className="py-8 text-center text-muted">Reviewing your recent performance…</p>
            ) : (
              <>
                <div className="mt-5 rounded-input border border-accent/30 bg-accent-soft/30 p-4">
                  <p className="flex items-center gap-2 text-sm font-bold text-ink"><Lightbulb size={18} className="text-accent" /> Focus points</p>
                  <ul className="mt-3 space-y-2 text-sm leading-6 text-ink">
                    {tips.map((tip) => <li key={tip} className="flex gap-2"><span className="mt-1 text-accent">•</span><span>{tip}</span></li>)}
                  </ul>
                </div>
                {error && <p className="mt-3 text-xs text-muted">Live performance data was unavailable, so we&rsquo;re showing the plan recommendation.</p>}
                <div className="mt-5 flex flex-wrap justify-end gap-2">
                  <Button variant="secondary" onClick={() => setOpen(false)}>Not yet</Button>
                  <Button onClick={() => navigate(task.destination)}><CheckCircle2 size={17} /> Start lesson</Button>
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </>
  )
}
