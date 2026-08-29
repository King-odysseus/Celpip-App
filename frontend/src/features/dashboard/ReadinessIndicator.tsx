import { ShieldCheck } from 'lucide-react'
import { Card, CardTitle, Meter } from '../../components/ui'
import type { Readiness } from '../learning/types'

function weightLabel(weight: number): string {
  return `${Math.round(weight * 100)}% weight`
}

/** Transparent practice planning indicator with its component inputs and disclaimer. */
export function ReadinessIndicator({ readiness }: { readiness: Readiness }) {
  const insufficient = readiness.state === 'insufficient_evidence'

  return (
    <Card>
      <div className="flex items-start gap-3">
        <ShieldCheck size={22} className="mt-0.5 shrink-0 text-accent" aria-hidden />
        <div className="min-w-0 flex-1">
          <CardTitle className="mb-1">{readiness.label}</CardTitle>
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-warn">
            Unofficial · not a CELPIP score
          </p>

          {insufficient ? (
            <p className="text-sm text-muted">{readiness.explanation}</p>
          ) : (
            <>
              <p className="text-4xl font-semibold tabular-nums text-ink">
                {readiness.indicator}
                <span className="text-lg text-muted">/100</span>
              </p>
              <div className="mt-2">
                <Meter
                  value={readiness.indicator ?? 0}
                  label={`${readiness.label}: ${readiness.indicator} of 100`}
                />
              </div>
              <p className="mt-2 text-sm text-muted">{readiness.explanation}</p>
            </>
          )}

          <p className="mt-3 text-xs tabular-nums text-muted">{readiness.formula}</p>

          <dl className="mt-3 space-y-2">
            {readiness.components.map((component) => (
              <div
                key={component.key}
                className="rounded-lg border border-line p-3"
              >
                <dt className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="text-sm font-semibold text-ink">
                    {component.label}{' '}
                    <span className="text-xs font-normal text-muted">
                      ({weightLabel(component.weight)})
                    </span>
                  </span>
                  <span className="text-sm tabular-nums text-brand">{component.value}/100</span>
                </dt>
                <dd className="mt-1 text-xs text-muted">{component.raw}</dd>
                <dd className="mt-1 text-xs text-muted">{component.explanation}</dd>
              </div>
            ))}
          </dl>

          <p className="mt-3 text-xs leading-5 text-muted">{readiness.disclaimer}</p>
        </div>
      </div>
    </Card>
  )
}
