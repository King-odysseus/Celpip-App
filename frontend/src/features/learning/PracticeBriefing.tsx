import { Lightbulb, X } from 'lucide-react'
import { Button, Card } from '../../components/ui'

export type BriefingTask = {
  title: string
  strategy: string[]
  common_mistakes: string[]
}

export function PracticeBriefing({ task, onCancel, onStart, starting }: { task: BriefingTask; onCancel: () => void; onStart: () => void; starting: boolean }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy/60 p-4" role="dialog" aria-modal="true" aria-labelledby="practice-briefing-title">
      <Card className="max-h-[90vh] w-full max-w-xl overflow-y-auto">
        <div className="flex items-start justify-between gap-3">
          <div><p className="eyebrow">Before you begin</p><h2 id="practice-briefing-title" className="mt-1 text-2xl font-bold text-ink">Your {task.title} focus</h2></div>
          <button type="button" aria-label="Close briefing" onClick={onCancel} className="rounded-full p-2 text-muted hover:bg-surface-secondary"><X size={20} /></button>
        </div>
        <div className="mt-5 rounded-input border border-accent/30 bg-accent-soft/25 p-4">
          <p className="flex items-center gap-2 text-sm font-bold text-ink"><Lightbulb size={17} className="text-accent" /> Approach</p>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm leading-6 text-ink">{task.strategy.slice(0, 3).map((step) => <li key={step}>{step}</li>)}</ol>
        </div>
        {task.common_mistakes[0] && <p className="mt-4 text-sm leading-6 text-ink"><strong>Watch for:</strong> {task.common_mistakes[0]}</p>}
        <p className="mt-2 text-xs text-muted">The activity timer starts after you continue.</p>
        <div className="mt-5 flex justify-end gap-2"><Button variant="secondary" onClick={onCancel}>Not yet</Button><Button disabled={starting} onClick={onStart}>{starting ? 'Starting…' : 'Start practice'}</Button></div>
      </Card>
    </div>
  )
}
