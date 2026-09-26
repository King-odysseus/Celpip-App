import { CheckCircle2, ListOrdered, RotateCcw, XCircle } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Button } from '../../components/ui'
import { api } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'
import type { AnswerPattern, PatternDrillProgress } from './types'

/**
 * Answer patterns: the memorable structure the app teaches for each Speaking
 * and Writing task type. The card teaches it, the drill makes the learner
 * recall it before practice, and the planner lets them fill it in during
 * preparation. Once a pattern is mastered, every surface shrinks to the
 * mnemonic alone so the learner relies on memory rather than the hint.
 */

export function PatternCard({ pattern, compact = false }: { pattern: AnswerPattern; compact?: boolean }) {
  return (
    <div className="rounded-input border border-accent/30 bg-accent-soft/25 p-4">
      <p className="text-xs font-bold uppercase tracking-widest text-accent">Answer pattern</p>
      <p className="mt-1 text-2xl font-bold tracking-wide text-ink">{pattern.mnemonic}</p>
      {compact ? (
        <p className="mt-1 text-sm text-ink">{pattern.steps.map((step) => step.label).join(' → ')}</p>
      ) : (
        <>
          <p className="mt-1 text-sm leading-6 text-ink">{pattern.summary}</p>
          <ol className="mt-3 space-y-2">
            {pattern.steps.map((step) => (
              <li key={step.key} className="text-sm leading-6">
                <details>
                  <summary className="cursor-pointer text-ink"><strong>{step.label}</strong> — {step.what}</summary>
                  <ul className="mt-1 list-disc space-y-0.5 pl-5 text-muted">
                    {step.phrases.map((phrase) => <li key={phrase}>{phrase}</li>)}
                  </ul>
                </details>
              </li>
            ))}
          </ol>
          <p className="mt-3 text-xs text-muted">{pattern.plan}</p>
        </>
      )}
    </div>
  )
}

function shuffled<T>(items: T[]): T[] {
  if (items.length < 2) return items
  let result = items
  // A drill that starts in the right order teaches nothing, so reshuffle.
  while (result.every((item, index) => item === items[index])) {
    result = [...items]
    for (let index = result.length - 1; index > 0; index -= 1) {
      const swap = Math.floor(Math.random() * (index + 1))
      ;[result[index], result[swap]] = [result[swap], result[index]]
    }
  }
  return result
}

/** Tap the steps of the pattern in order, from memory. */
export function PatternDrill({ pattern, onComplete }: { pattern: AnswerPattern; onComplete: (correct: boolean) => void }) {
  const labels = useMemo(() => pattern.steps.map((step) => step.label), [pattern])
  const [options, setOptions] = useState(() => shuffled(labels))
  const [picked, setPicked] = useState<string[]>([])
  const [result, setResult] = useState<'correct' | 'wrong' | null>(null)

  function pick(label: string) {
    if (result) return
    const next = [...picked, label]
    setPicked(next)
    if (label !== labels[next.length - 1]) {
      setResult('wrong')
      onComplete(false)
    } else if (next.length === labels.length) {
      setResult('correct')
      onComplete(true)
    }
  }

  function retry() {
    setOptions(shuffled(labels))
    setPicked([])
    setResult(null)
  }

  return (
    <div className="rounded-input border border-line bg-surface-secondary/60 p-4" aria-label="Pattern recall drill">
      <p className="flex items-center gap-2 text-sm font-bold text-ink"><ListOrdered size={17} className="text-brand" /> Recall the {pattern.mnemonic} pattern</p>
      <p className="mt-1 text-xs text-muted">Tap the steps in the order you'll use them.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {options.map((label) => {
          const position = picked.indexOf(label)
          return (
            <button
              key={label}
              type="button"
              disabled={position >= 0 || result !== null}
              onClick={() => pick(label)}
              className="min-h-10 rounded-full border border-line bg-surface px-3 py-1.5 text-sm font-semibold text-ink transition hover:border-brand disabled:cursor-default disabled:opacity-60"
            >
              {position >= 0 && <span className="mr-1 text-brand">{position + 1}.</span>}
              {label}
            </button>
          )
        })}
      </div>
      {result === 'correct' && (
        <p role="status" className="mt-3 flex items-center gap-2 text-sm font-semibold text-good"><CheckCircle2 size={17} /> Correct — {labels.join(' → ')}</p>
      )}
      {result === 'wrong' && (
        <div role="status" className="mt-3 text-sm">
          <p className="flex items-center gap-2 font-semibold text-bad"><XCircle size={17} /> Not quite. The order is {labels.join(' → ')}.</p>
          <Button variant="secondary" className="mt-2" onClick={retry}><RotateCcw size={16} /> Try again</Button>
        </div>
      )}
    </div>
  )
}

/** Blank outline for preparation time: a keyword or two per step. */
export function PatternPlanner({ pattern, compact = false }: { pattern: AnswerPattern; compact?: boolean }) {
  const [notes, setNotes] = useState<Record<string, string>>({})
  return (
    <div className="rounded-input border border-accent/30 bg-accent-soft/20 p-4">
      <p className="text-xs font-bold uppercase tracking-widest text-accent">Plan with {pattern.mnemonic}</p>
      <p className="mt-1 text-xs text-muted">Jot a keyword or two for each step while you prepare. Notes stay on this screen only.</p>
      <div className="mt-3 space-y-2">
        {pattern.steps.map((step) => (
          <label key={step.key} className="block text-sm">
            <span className="font-bold text-ink">{step.label}</span>
            {!compact && <span className="text-muted"> — {step.what}</span>}
            <input
              value={notes[step.key] ?? ''}
              onChange={(event) => setNotes((current) => ({ ...current, [step.key]: event.target.value }))}
              className="mt-1 w-full rounded-input border border-line bg-surface px-3 py-2 text-sm text-ink focus-visible:outline-2 focus-visible:outline-brand"
              placeholder={compact ? '' : step.phrases[0]}
            />
          </label>
        ))}
      </div>
    </div>
  )
}

/**
 * The signed-in learner's drill progress per task type. Guests can still
 * drill; their results just aren't saved.
 */
export function usePatternProgress() {
  const { status } = useAuth()
  const [progress, setProgress] = useState<Record<string, PatternDrillProgress>>({})

  useEffect(() => {
    if (status !== 'authenticated') return
    let cancelled = false
    api
      .get<{ results: PatternDrillProgress[] }>('/me/pattern-drills/')
      .then((response) => {
        if (!cancelled) setProgress(Object.fromEntries(response.results.map((item) => [item.task_type, item])))
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [status])

  const record = useCallback(
    (taskType: string, correct: boolean) => {
      if (status !== 'authenticated') return
      api
        .post<PatternDrillProgress>('/me/pattern-drills/', { task_type: taskType, correct })
        .then((item) => setProgress((current) => ({ ...current, [item.task_type]: item })))
        .catch(() => undefined)
    },
    [status],
  )

  return { progress, record }
}
