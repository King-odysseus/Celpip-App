import { Flame, ListChecks, Trophy } from 'lucide-react'
import { Card } from '../../components/ui'

/** Compact stat cards: streak, total objective questions, completed attempts. */
export function DashboardStats({
  streakDays,
  totalQuestions,
  completedAttempts,
}: {
  streakDays: number
  totalQuestions: number
  completedAttempts: number
}) {
  const stats = [
    {
      icon: Flame,
      label: 'Day streak',
      value: `${streakDays}`,
      hint: streakDays === 1 ? 'day' : 'days',
    },
    {
      icon: ListChecks,
      label: 'Objective questions',
      value: `${totalQuestions}`,
      hint: 'completed',
    },
    {
      icon: Trophy,
      label: 'Completed attempts',
      value: `${completedAttempts}`,
      hint: 'across all skills',
    },
  ]

  return (
    <div className="grid h-fit gap-3 self-start sm:col-span-2 sm:grid-cols-3 lg:col-span-3">
      {stats.map(({ icon: Icon, label, value, hint }) => (
        <Card key={label} className="!p-3 h-fit min-h-0 flex items-start gap-2">
          <Icon size={19} className="mt-0.5 shrink-0 text-accent" aria-hidden />
          <div className="min-w-0">
            <p className="text-lg font-semibold tabular-nums text-ink">{value}</p>
            <p className="text-xs leading-4 text-muted">
              {label}
              {hint ? <span> · {hint}</span> : null}
            </p>
          </div>
        </Card>
      ))}
    </div>
  )
}
