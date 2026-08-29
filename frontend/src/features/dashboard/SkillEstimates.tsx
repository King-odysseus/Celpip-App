import { Card, CardTitle, Meter } from '../../components/ui'
import { SKILLS } from '../auth/types'
import type { Progress } from '../learning/types'
import { SKILL_LABELS } from './labels'

/** The four per-skill summaries, keeping objective accuracy separate from AI estimates. */
export function SkillEstimates({ skills }: { skills: Progress['skills'] }) {
  return (
    <section aria-labelledby="skill-estimates-title">
      <h2
        id="skill-estimates-title"
        className="mb-3 text-lg font-semibold tracking-tight text-ink"
      >
        Skill estimates
      </h2>
      <div className="grid gap-4 sm:grid-cols-2">
        {SKILLS.map((skill) => {
          const summary = skills.find((item) => item.skill === skill)
          const measure =
            summary?.accuracy_percent !== null && summary?.accuracy_percent !== undefined
              ? `${summary.accuracy_percent}% accuracy`
              : summary?.estimate_low !== null && summary?.estimate_low !== undefined
                ? `Estimated ${summary.estimate_low}–${summary.estimate_high}`
                : '—'
          const meterValue =
            summary?.accuracy_percent ??
            (summary?.estimate_high ? (summary.estimate_high / 12) * 100 : 0)
          return (
            <Card key={skill}>
              <div className="mb-2 flex items-center justify-between">
                <CardTitle>{SKILL_LABELS[skill]}</CardTitle>
                <span className="text-sm tabular-nums text-muted">{measure}</span>
              </div>
              <Meter value={meterValue} label={`${SKILL_LABELS[skill]}: ${measure}`} />
              <p className="mt-2 text-sm text-muted">
                {summary?.attempts
                  ? `${summary.attempts} completed attempt${summary.attempts === 1 ? '' : 's'}.`
                  : 'No practice recorded yet.'}
              </p>
            </Card>
          )
        })}
      </div>
    </section>
  )
}
