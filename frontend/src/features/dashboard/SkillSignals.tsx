import { Award, TrendingUp } from 'lucide-react'
import { Card, CardTitle, Meter } from '../../components/ui'
import type { Dashboard } from '../learning/types'
import { SKILL_LABELS } from './labels'

function SignalCard({
  tone,
  icon: Icon,
  title,
  signal,
}: {
  tone: 'good' | 'warn'
  icon: typeof Award
  title: string
  signal: Dashboard['signals']['strongest']
}) {
  const label = signal ? SKILL_LABELS[signal.skill] : '—'
  return (
    <Card>
      <div className="mb-2 flex items-center gap-2">
        <Icon size={20} className={tone === 'good' ? 'text-good' : 'text-warn'} aria-hidden />
        <CardTitle>{title}</CardTitle>
      </div>
      {signal ? (
        <>
          <p className="text-xl font-semibold text-ink">{label}</p>
          <p className="mt-1 text-sm text-muted">{signal.basis}</p>
          {signal.planning_signal !== null && (
            <div className="mt-3">
              <Meter
                value={signal.planning_signal}
                label={`${label} practice planning signal: ${signal.planning_signal}`}
              />
              <p className="mt-1 text-xs tabular-nums text-muted">
                {signal.planning_signal}/100 practice planning signal
              </p>
            </div>
          )}
        </>
      ) : (
        <p className="text-sm text-muted">No practice recorded yet.</p>
      )}
    </Card>
  )
}

/** Strongest and needs-attention practice signals, with their metric basis. */
export function SkillSignals({ signals }: { signals: Dashboard['signals'] }) {
  return (
    <section aria-labelledby="skill-signals-title">
      <h2
        id="skill-signals-title"
        className="mb-3 text-lg font-semibold tracking-tight text-ink"
      >
        Practice signals
      </h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <SignalCard tone="good" icon={Award} title="Strongest skill" signal={signals.strongest} />
        <SignalCard
          tone="warn"
          icon={TrendingUp}
          title="Needs attention"
          signal={signals.needs_attention}
        />
      </div>
      <p className="mt-2 text-xs text-muted">{signals.note}</p>
    </section>
  )
}
