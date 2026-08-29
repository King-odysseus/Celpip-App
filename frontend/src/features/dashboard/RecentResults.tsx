import { Link } from 'react-router-dom'
import { Card, CardTitle } from '../../components/ui'
import type { RecentResult } from '../learning/types'
import { SKILL_LABELS } from './labels'

function formatValue(measure: RecentResult['measure'], value: number): string {
  if (measure === 'accuracy_percent') return `${value}%`
  return `${value}/12 midpoint`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
}

/** Most-recent submitted results, newest first and privacy-safe. */
export function RecentResults({ results }: { results: RecentResult[] }) {
  return (
    <Card>
      <CardTitle className="mb-3">Recent results</CardTitle>
      {results.length === 0 ? (
        <p className="text-sm text-muted">
          No completed attempts yet.{' '}
          <Link to="/practice" className="font-semibold text-brand hover:underline">
            Start focused practice
          </Link>
          .
        </p>
      ) : (
        <ul className="space-y-2">
          {results.map((result, index) => (
            <li
              key={`${result.date}-${result.task_type}-${index}`}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line p-3"
            >
              <div className="min-w-0">
                <p className="text-sm font-semibold text-ink">{result.title}</p>
                <p className="text-xs text-muted">
                  {SKILL_LABELS[result.skill]} · {result.label} · {formatDate(result.date)}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold tabular-nums text-brand">
                  {formatValue(result.measure, result.value)}
                </span>
                <Link
                  to={result.destination}
                  className="text-sm font-semibold text-brand hover:underline"
                >
                  Open
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
