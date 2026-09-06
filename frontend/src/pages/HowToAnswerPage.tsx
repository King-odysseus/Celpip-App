import { BookOpen, CheckCircle2, Headphones, Mic2, PenLine, Sparkles, type LucideIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { LEVEL_TWELVE_GUIDANCE } from '../features/learning/levelTwelveGuidance'
import { TaskTypeGuides } from '../features/learning/TaskTypeGuides'
import type { Skill, TaskTypeGuide } from '../features/learning/types'
import { api } from '../lib/api'

const SKILLS: Array<{ skill: Skill; label: string; icon: LucideIcon; partLabel: string }> = [
  { skill: 'listening', label: 'Listening', icon: Headphones, partLabel: 'Part' },
  { skill: 'reading', label: 'Reading', icon: BookOpen, partLabel: 'Part' },
  { skill: 'writing', label: 'Writing', icon: PenLine, partLabel: 'Task' },
  { skill: 'speaking', label: 'Speaking', icon: Mic2, partLabel: 'Task' },
]

export function HowToAnswerPage() {
  const [active, setActive] = useState<Skill>('listening')
  const [taskTypesBySkill, setTaskTypesBySkill] = useState<Partial<Record<Skill, TaskTypeGuide[]>>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    Promise.all(
      SKILLS.map(({ skill }) =>
        api.get<TaskTypeGuide[]>(`/content/task-types/?skill=${skill}`).then((types) => [skill, types] as const),
      ),
    )
      .then((pairs) => {
        if (cancelled) return
        const byskill: Partial<Record<Skill, TaskTypeGuide[]>> = {}
        for (const [skill, types] of pairs) byskill[skill] = types
        setTaskTypesBySkill(byskill)
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : 'Could not load guidance.')
      })
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  const guide = LEVEL_TWELVE_GUIDANCE[active]
  const taskTypes = taskTypesBySkill[active] ?? []
  const activeMeta = SKILLS.find((entry) => entry.skill === active)!

  return (
    <div className="mx-auto w-full max-w-[1600px] space-y-8 animate-fade-up">
      <header className="rounded-card bg-brand px-5 py-8 text-white shadow-elevated sm:px-8">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent-soft">The method, not just more questions</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">How to Answer</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-white/80 sm:text-base">
          For each skill: a reliable approach for every task type, the mistakes that quietly cost marks, and what
          separates a solid response from a top-band (11–12) one.
        </p>
      </header>

      <nav aria-label="Skill" className="flex flex-wrap gap-2">
        {SKILLS.map(({ skill, label, icon: Icon }) => (
          <button
            key={skill}
            type="button"
            aria-current={active === skill ? 'page' : undefined}
            onClick={() => setActive(skill)}
            className={`flex min-h-11 items-center gap-2 rounded-full px-4 py-2 text-sm font-bold transition ${
              active === skill ? 'bg-brand text-white' : 'bg-surface-secondary text-ink hover:bg-brand-soft'
            }`}
          >
            <Icon size={17} /> {label}
          </button>
        ))}
      </nav>

      {error && <p role="alert" className="rounded-input bg-bad-soft p-3 text-sm text-bad">{error}</p>}

      <section aria-labelledby="level-12-title" className="rounded-card border border-accent/30 bg-accent-soft/25 p-6">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-accent">
          <Sparkles size={16} /> Reaching level 11–12 in {activeMeta.label}
        </p>
        <h2 id="level-12-title" className="mt-2 text-xl font-bold text-ink">{guide.headline}</h2>
        <p className="mt-2 text-sm leading-6 text-ink">{guide.keyShift}</p>
        <ul className="mt-4 space-y-2">
          {guide.checklist.map((item) => (
            <li key={item} className="flex items-start gap-2 text-sm leading-6 text-ink">
              <CheckCircle2 size={17} className="mt-0.5 shrink-0 text-accent" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </section>

      {loading ? (
        <p role="status" className="py-10 text-center text-muted">Loading task-type guidance…</p>
      ) : (
        <TaskTypeGuides
          taskTypes={taskTypes}
          headingId="how-to-answer-task-guides"
          eyebrow={`Know the ${activeMeta.label.toLowerCase()} task types`}
          icon={activeMeta.icon}
          partLabel={activeMeta.partLabel}
        />
      )}
    </div>
  )
}
