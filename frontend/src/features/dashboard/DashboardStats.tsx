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
    <div className="grid gap-4 sm:grid-cols-3">
      {stats.map(({ icon: Icon, label, value, hint }) => (
        <Card key={label} className="flex items-center gap-3">
          <Icon size={22} className="shrink-0 text-accent" aria-hidden />
          <div className="min-w-0">
            <p className="text-2xl font-semibold tabular-nums text-ink">{value}</p>
            <p className="text-sm text-muted">
              {label}
              {hint ? <span className="text-xs"> · {hint}</span> : null}
            </p>
          </div>
        </Card>
      ))}
    </div>
  )
}
