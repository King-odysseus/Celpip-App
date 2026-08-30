import { Bot } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Card, CardTitle } from '../../components/ui'
import { api } from '../../lib/api'
import { DIMENSION_LABELS } from '../ai/dimensionLabels'
import type { Skill } from '../learning/types'
import { SKILL_LABELS } from './labels'

type Dimension = { key: string; rating: number; evidence: string; next_step: string }

type Assessment = {
  overall_summary: string
  dimensions: Dimension[]
  strengths: string[]
  priorities: string[]
  estimated_level_low: number
  estimated_level_high: number
  confidence: 'low' | 'medium' | 'high'
  disclaimer: string
}

type HistoryEntry = {
  created_at: string
  kind: string
  skill: Skill
  task_type: string
  title: string
  estimated_level_low: number
  estimated_level_high: number
  transcript: string
  assessment: Assessment
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
}

function Entry({ entry }: { entry: HistoryEntry }) {
  const assessment = entry.assessment
  return (
    <details className="group rounded-lg border border-line p-3 open:bg-surface-secondary/60">
      <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-ink">{entry.title}</p>
          <p className="text-xs text-muted">
            {SKILL_LABELS[entry.skill]} · {formatDate(entry.created_at)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold tabular-nums text-brand">
            {entry.estimated_level_low}–{entry.estimated_level_high}
          </span>
          <ChevronDownIcon />
        </div>
      </summary>
      <div className="mt-3 space-y-3">
        <p className="text-sm leading-6 text-muted">{assessment.overall_summary}</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {assessment.dimensions.map((dimension) => (
            <div key={dimension.key} className="rounded-lg bg-surface p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-bold text-ink">
                  {DIMENSION_LABELS[dimension.key] ?? dimension.key}
                </p>
                <span className="rounded-full bg-brand-soft px-2 py-0.5 text-[11px] font-bold text-brand">
                  {dimension.rating}/4
                </span>
              </div>
              <p className="mt-2 text-xs leading-5 text-muted">{dimension.evidence}</p>
              <p className="mt-1.5 text-xs leading-5 text-muted">
                <strong className="text-ink">Next step:</strong> {dimension.next_step}
              </p>
            </div>
          ))}
        </div>
        {assessment.strengths.length > 0 && (
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-muted">Strengths</p>
            <ul className="mt-1 list-inside list-disc space-y-0.5 text-sm text-muted">
              {assessment.strengths.map((strength) => (
                <li key={strength}>{strength}</li>
              ))}
            </ul>
          </div>
        )}
        {assessment.priorities.length > 0 && (
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-muted">Priorities</p>
            <ul className="mt-1 list-inside list-disc space-y-0.5 text-sm text-muted">
              {assessment.priorities.map((priority) => (
                <li key={priority}>{priority}</li>
              ))}
            </ul>
          </div>
        )}
        {entry.transcript && (
          <details className="rounded-lg bg-surface p-3 text-xs">
            <summary className="cursor-pointer font-semibold text-ink">
              AI transcript used for feedback
            </summary>
            <p className="mt-2 whitespace-pre-wrap leading-5 text-muted">{entry.transcript}</p>
          </details>
        )}
      </div>
    </details>
  )
}

function ChevronDownIcon() {
  return (
    <span
      aria-hidden
      className="text-muted transition-transform group-open:rotate-180"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="m6 9 6 6 6-6" />
      </svg>
    </span>
  )
}

/**
 * Revisitable AI-assisted feedback (transcript + analysis + score) for the last
 * 50 days, newest first. Audio is never shown — it is discarded after analysis.
 */
export function FeedbackHistory() {
  const [entries, setEntries] = useState<HistoryEntry[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    api
      .get<{ results: HistoryEntry[] }>('/me/ai-feedback/history/')
      .then((data) => {
        if (active) setEntries(data.results)
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(
            reason instanceof Error ? reason.message : 'Could not load feedback history.',
          )
        }
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <Card>
      <CardTitle className="flex items-center gap-2">
        <Bot size={20} className="text-accent" aria-hidden />
        Feedback history
      </CardTitle>
      <p className="mt-1 text-sm text-muted">
        AI-assisted transcript, analysis, and score for your recent Writing and
        Speaking attempts, kept for 50 days.
      </p>
      {error ? (
        <p role="alert" className="mt-3 rounded-input bg-bad-soft p-3 text-bad">{error}</p>
      ) : entries.length === 0 ? (
        <p className="mt-3 text-sm text-muted">
          No AI feedback yet. Submit a Writing or Speaking attempt to receive an
          analysis you can revisit here.
        </p>
      ) : (
        <div className="mt-3 space-y-2">
          {entries.map((entry, index) => (
            <Entry key={`${entry.created_at}-${index}`} entry={entry} />
          ))}
        </div>
      )}
    </Card>
  )
}
