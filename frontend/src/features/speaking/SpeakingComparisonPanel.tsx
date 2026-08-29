import {
  AlertTriangle,
  Bot,
  ExternalLink,
  Loader2,
  ShieldCheck,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { ButtonLink, Card } from '../../components/ui'
import { getSpeakingComparison } from './api'
import { tokenHeaders } from './token'
import type {
  SpeakingComparison,
  SpeakingComparisonAttemptState,
  SpeakingComparisonEstimate,
} from './types'

const POLL_MS = 3000

function feedbackStatusLabel(state: SpeakingComparisonAttemptState): string {
  if (state.feedback_status === 'ready') return 'Feedback ready'
  if (state.feedback_status === 'failed') return 'Feedback could not be completed'
  switch (state.job_status) {
    case 'running':
      return 'Being evaluated'
    case 'queued':
      return 'Queued for evaluation'
    case 'succeeded':
      return 'Finalizing feedback'
    default:
      return 'Waiting to be evaluated'
  }
}

function formatSigned(value: number): string {
  return value > 0 ? `+${value}` : `${value}`
}

function midpointChange(delta: number): { word: string; sign: string } {
  if (delta > 0) return { word: 'Increased', sign: formatSigned(delta) }
  if (delta < 0) return { word: 'Decreased', sign: formatSigned(delta) }
  return { word: 'No change', sign: '0' }
}

function dimensionDeltaWord(delta: number | null): string {
  if (delta === null) return 'Not rated'
  if (delta > 0) return 'Increased'
  if (delta < 0) return 'Decreased'
  return 'No change'
}

/**
 * Cohesive attempt 1 vs attempt 2 comparison for a submitted Attempt 2 review.
 * It polls while feedback is pending and never fetches or exposes raw audio.
 */
export function SpeakingComparisonPanel({ sessionId }: { sessionId: string }) {
  const [comparison, setComparison] = useState<SpeakingComparison | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    let timer = 0
    const load = async () => {
      try {
        const result = await getSpeakingComparison(sessionId, tokenHeaders(sessionId))
        if (!active) return
        setComparison(result)
        if (result.status === 'pending') {
          timer = window.setTimeout(() => void load(), POLL_MS)
        }
      } catch (reason) {
        if (active) {
          setError(reason instanceof Error ? reason.message : 'Could not load the comparison.')
        }
      }
    }
    void load()
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [sessionId])

  if (error) {
    return (
      <Card className="border-dashed p-5" role="alert">
        <h2 className="flex items-center gap-2 text-xl font-bold text-ink">
          <AlertTriangle className="text-bad" size={21} /> Comparison unavailable
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted">{error}</p>
      </Card>
    )
  }
  if (!comparison) {
    return (
      <Card className="border-dashed p-5" role="status" aria-live="polite">
        <h2 className="flex items-center gap-2 text-xl font-bold text-ink">
          <Loader2 className="animate-spin text-brand" size={21} /> Loading your comparison…
        </h2>
      </Card>
    )
  }
  if (comparison.status === 'pending') return <PendingView comparison={comparison} />
  if (comparison.status === 'failed') return <FailedView comparison={comparison} />
  return <ReadyView comparison={comparison} />
}

function PendingView({ comparison }: { comparison: SpeakingComparison }) {
  return (
    <Card className="border-dashed p-5" role="status" aria-live="polite">
      <h2 className="flex items-center gap-2 text-xl font-bold text-ink">
        <Loader2 className="animate-spin text-brand" size={21} /> Comparing your two attempts
      </h2>
      <p className="mt-2 text-sm leading-6 text-muted">
        AI-assisted feedback is still being prepared for one or both attempts. This page updates
        automatically.
      </p>
      <ul className="mt-4 space-y-2 text-sm text-ink">
        <li><strong>Attempt 1:</strong> {feedbackStatusLabel(comparison.attempts['1'])}</li>
        <li><strong>Attempt 2:</strong> {feedbackStatusLabel(comparison.attempts['2'])}</li>
      </ul>
    </Card>
  )
}

function FailedView({ comparison }: { comparison: SpeakingComparison }) {
  const failed = (Object.entries(comparison.attempts) as [string, SpeakingComparisonAttemptState][])
    .filter(([, state]) => state.feedback_status === 'failed')
  return (
    <Card className="border-dashed p-5">
      <h2 className="flex items-center gap-2 text-xl font-bold text-ink">
        <AlertTriangle className="text-bad" size={21} /> Comparison unavailable
      </h2>
      <p className="mt-2 text-sm leading-6 text-muted">
        AI-assisted feedback could not be completed for one of your attempts, so the two attempts
        cannot be compared.
      </p>
      <ul className="mt-4 space-y-2 text-sm text-ink" role="alert">
        {failed.map(([number, state]) => (
          <li key={number}>
            <strong>Attempt {number}:</strong>{' '}
            {state.error ?? 'AI-assisted feedback could not be completed for this attempt.'}
            {state.error_code && <span className="text-xs text-muted"> (code {state.error_code})</span>}
          </li>
        ))}
      </ul>
    </Card>
  )
}

function UnavailableView() {
  return (
    <Card className="border-dashed p-5" role="alert">
      <h2 className="flex items-center gap-2 text-xl font-bold text-ink">
        <AlertTriangle className="text-bad" size={21} /> Comparison unavailable
      </h2>
      <p className="mt-2 text-sm leading-6 text-muted">
        The two attempts could not be compared. Your individual feedback is still available from
        each attempt's review page.
      </p>
    </Card>
  )
}

function ReadyView({ comparison }: { comparison: SpeakingComparison }) {
  const attempt1 = comparison.attempt_1
  const attempt2 = comparison.attempt_2
  if (!attempt1 || !attempt2) return <UnavailableView />
  const change = midpointChange(comparison.midpoint_delta ?? 0)
  const dimensions = comparison.dimension_deltas ?? []
  const improvements = comparison.improvements ?? []
  const priorities = comparison.remaining_priorities ?? []

  return (
    <section aria-label="Speaking comparison" className="space-y-4">
      <Card className="overflow-hidden p-0">
        <div className="bg-brand px-5 py-6 text-white">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-accent-soft">
            <Bot size={17} /> AI-assisted practice comparison
          </p>
          <h2 className="mt-2 text-2xl font-bold">Attempt 1 vs Attempt 2</h2>
        </div>
        <p className="flex items-start gap-2 p-4 text-sm text-muted">
          <ShieldCheck className="mt-0.5 shrink-0 text-good" size={18} /> {comparison.disclaimer}
        </p>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        <EstimateCard number={1} estimate={attempt1} />
        <EstimateCard number={2} estimate={attempt2} />
      </div>

      <Card className="p-5">
        <h3 className="text-lg font-semibold text-ink">Estimated midpoint change</h3>
        <div
          className="mt-2 flex flex-wrap items-center gap-3"
          role="group"
          aria-label="Estimated midpoint change result"
        >
          <span className="text-3xl font-bold text-ink">{change.word}</span>
          <span className="rounded-full bg-brand-soft px-3 py-1 text-xl tabular-nums text-brand">
            {change.sign}
          </span>
        </div>
        <p className="mt-3 text-sm text-warn">
          A midpoint change is not an official score difference.
        </p>
      </Card>

      <Card className="p-5">
        <h3 className="text-lg font-semibold text-ink">Dimension ratings</h3>
        <ul className="mt-4 space-y-4">
          {dimensions.map((dimension) => (
            <li key={dimension.key} className="rounded-input border border-line p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-bold text-ink">{dimension.label}</span>
                <span className="text-sm font-bold text-accent">
                  {dimensionDeltaWord(dimension.delta)}
                  {dimension.delta !== null && ` (${formatSigned(dimension.delta)})`}
                </span>
              </div>
              <p className="mt-2 text-sm text-muted">
                Attempt 1: {dimension.rating_1 ?? '—'} · Attempt 2: {dimension.rating_2 ?? '—'}
              </p>
            </li>
          ))}
        </ul>
      </Card>

      <Card className="p-5">
        <h3 className="text-lg font-semibold text-ink">Improvements</h3>
        {improvements.length ? (
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-6 text-ink">
            {improvements.map((improvement, index) => (
              <li key={index}>
                {improvement.kind === 'dimension' ? (
                  <><strong>{improvement.label}</strong>: {improvement.evidence}</>
                ) : (
                  improvement.text
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-muted">No clear improvements were detected between the two attempts.</p>
        )}
      </Card>

      <Card className="p-5">
        <h3 className="text-lg font-semibold text-ink">Still to work on</h3>
        {priorities.length ? (
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-6 text-ink">
            {priorities.map((priority) => <li key={priority}>{priority}</li>)}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-muted">No remaining priorities were identified for this attempt.</p>
        )}
      </Card>

      <details className="card p-5">
        <summary className="cursor-pointer text-sm font-bold text-ink focus-visible:outline-2 focus-visible:outline-brand">
          Comparison audit details
        </summary>
        <dl className="mt-3 space-y-2 text-xs text-muted">
          <div><dt className="inline font-semibold">Attempt 1:</dt> <dd className="inline">{attempt1.audit.provider} · {attempt1.audit.model} · prompt {attempt1.audit.prompt_version}</dd></div>
          <div><dt className="inline font-semibold">Attempt 2:</dt> <dd className="inline">{attempt2.audit.provider} · {attempt2.audit.model} · prompt {attempt2.audit.prompt_version}</dd></div>
        </dl>
      </details>

      <div className="flex flex-wrap gap-3">
        <ButtonLink to={`/speaking/session/${attempt1.session_id}`} variant="secondary">
          <ExternalLink size={16} /> Open Attempt 1 review
        </ButtonLink>
        <ButtonLink to={`/speaking/session/${attempt2.session_id}`} variant="secondary">
          <ExternalLink size={16} /> Open Attempt 2 review
        </ButtonLink>
      </div>
    </section>
  )
}

function EstimateCard({ number, estimate }: { number: 1 | 2; estimate: SpeakingComparisonEstimate }) {
  return (
    <Card className="p-5 text-center">
      <p className="eyebrow">Attempt {number}</p>
      <p className="mt-2 text-3xl font-bold tabular-nums text-ink">
        {estimate.estimated_range.low}–{estimate.estimated_range.high}
      </p>
      <p className="mt-1 text-sm text-muted">Estimated midpoint {estimate.estimated_midpoint}</p>
    </Card>
  )
}
