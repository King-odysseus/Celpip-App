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
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {SKILLS.map((skill) => {
          const summary = skills.find((item) => item.skill === skill)
          const measure =
            summary?.accuracy_percent !== null && summary?.accuracy_percent !== undefined
              ? `${summary.accuracy_percent}% practice accuracy`
              : summary?.estimate_low !== null && summary?.estimate_low !== undefined
                ? `Estimated ${summary.estimate_low}–${summary.estimate_high}`
                : '—'
          const meterValue =
            summary?.accuracy_percent ??
            (summary?.estimate_high ? (summary.estimate_high / 12) * 100 : 0)
          return (
            <Card key={skill} className="!p-4">
              <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-2 gap-y-0.5">
                <CardTitle>{SKILL_LABELS[skill]}</CardTitle>
                <span className="text-sm tabular-nums text-muted">{measure}</span>
              </div>
              <Meter value={meterValue} label={`${SKILL_LABELS[skill]}: ${measure}`} />
              {summary?.practice_range_low != null && summary.practice_range_high != null && (
                <p className="mt-2 text-xs leading-5 text-muted">
                  Indicative practice range:{' '}
                  <span className="font-semibold text-ink">CELPIP {summary.practice_range_low}–{summary.practice_range_high}</span>
                  <br />Based on {summary.questions_total} objective questions · unofficial
                </p>
              )}
              <p className="mt-2 text-sm text-muted">
                {summary?.attempts
                  ? `${summary.attempts} completed attempt${summary.attempts === 1 ? '' : 's'}.`
                  : 'No practice recorded yet.'}
              </p>
              <p className="mt-1 text-xs text-muted">
                Target: <span className="font-semibold text-ink">CELPIP {summary?.target ?? '—'}</span>
                {summary && summary.estimate_high !== null && summary.estimate_high !== undefined && summary.target > summary.estimate_high
                  ? ` · ${summary.target - summary.estimate_high} level${summary.target - summary.estimate_high === 1 ? '' : 's'} below target range`
                  : ''}
              </p>
            </Card>
          )
        })}
      </div>
    </section>
  )
}
