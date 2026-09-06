import { BookOpenCheck, type LucideIcon } from 'lucide-react'
import type { TaskTypeGuide } from './types'

/**
 * Expandable per-task-type guides: what the task asks, a reliable approach,
 * and mistakes to watch for. Shared by every skill's Learn catalog and by the
 * standalone How to Answer reference so the guidance reads identically
 * everywhere it appears.
 */
export function TaskTypeGuides({
  taskTypes,
  headingId,
  eyebrow = 'Know the task types',
  icon: Icon = BookOpenCheck,
  partLabel = 'Part',
}: {
  taskTypes: TaskTypeGuide[]
  headingId: string
  eyebrow?: string
  icon?: LucideIcon
  partLabel?: string
}) {
  return (
    <section aria-labelledby={headingId}>
      <p className="eyebrow">{eyebrow}</p>
      <h2 id={headingId} className="mt-1 text-2xl font-bold text-ink">Task-type guides</h2>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {taskTypes.map((task) => (
          <details key={task.code} className="card group p-5">
            <summary className="flex cursor-pointer list-none items-center gap-3 font-bold text-ink focus-visible:outline-2 focus-visible:outline-brand">
              <Icon className="text-accent" size={21} />
              <span>{partLabel} {task.part_number}: {task.title}</span>
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
