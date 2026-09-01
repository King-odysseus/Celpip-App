import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import { Card } from '../../components/ui'
import type { Progress, Skill } from './types'

const labels: Record<Skill, string> = { listening: 'Listening', reading: 'Reading', writing: 'Writing', speaking: 'Speaking' }

function trendFor(progress: Progress, skill: Skill): { label: string; tone: string; Icon: typeof ArrowUpRight } {
  const values = progress.trends
    .filter((item) => item.skill === skill)
    .slice(-2)
  if (values.length < 2) return { label: values.length ? 'Baseline recorded' : 'No evidence yet', tone: 'text-muted', Icon: Minus }
  const change = values[1].value - values[0].value
  if (change > 0) return { label: `Improving · +${change}`, tone: 'text-good', Icon: ArrowUpRight }
  if (change < 0) return { label: `Needs attention · ${change}`, tone: 'text-bad', Icon: ArrowDownRight }
  return { label: 'Holding steady', tone: 'text-muted', Icon: Minus }
}

/** A compact direction-of-travel summary; metrics are never combined across skills. */
export function ProgressTrendSummary({ progress }: { progress: Progress }) {
  return (
    <section aria-labelledby="trend-summary-title">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 id="trend-summary-title" className="text-xl font-bold text-ink">How you&rsquo;re moving</h2>
        <span className="text-xs text-muted">Compared with your previous result</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {(Object.keys(labels) as Skill[]).map((skill) => {
          const result = trendFor(progress, skill)
          const Icon = result.Icon
          return (
            <Card key={skill} className="p-4">
              <p className="text-sm font-semibold text-ink">{labels[skill]}</p>
              <p className={`mt-2 flex items-center gap-1 text-sm font-bold ${result.tone}`}>
                <Icon size={17} aria-hidden /> {result.label}
              </p>
            </Card>
          )
        })}
      </div>
    </section>
  )
}
