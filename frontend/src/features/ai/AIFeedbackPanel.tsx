import { Bot, Loader2, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Card } from '../../components/ui'
import { api } from '../../lib/api'
import { DIMENSION_LABELS } from './dimensionLabels'

type Dimension = { key: string; rating: number; evidence: string; next_step: string }
type FeedbackState = {
  status: 'not_requested' | 'queued' | 'running' | 'succeeded' | 'failed'
  error?: string
  transcript?: string
  assessment?: {
    overall_summary: string
    dimensions: Dimension[]
    strengths: string[]
    priorities: string[]
    estimated_level_low: number
    estimated_level_high: number
    confidence: 'low' | 'medium' | 'high'
    disclaimer: string
  }
  audit?: { provider: string; model: string; prompt_version: string; created_at: string }
}

function tokenHeaders(sessionId: string): Record<string, string> {
  const token = sessionStorage.getItem(`celpip-guest-${sessionId}`)
  return token ? { 'X-Guest-Token': token } : {}
}

export function AIFeedbackPanel({ sessionId }: { sessionId: string }) {
  const [feedback, setFeedback] = useState<FeedbackState | null>(null)
  const [unavailable, setUnavailable] = useState(false)

  useEffect(() => {
    let active = true
    let timer = 0
    const load = async () => {
      try {
        const result = await api.get<FeedbackState>(`/sessions/${sessionId}/ai-feedback/`, tokenHeaders(sessionId))
        if (!active) return
        setFeedback(result)
        setUnavailable(false)
        if (result.status === 'queued' || result.status === 'running') {
          timer = window.setTimeout(() => void load(), 3000)
        }
      } catch {
        if (active) setUnavailable(true)
      }
    }
    void load()
    return () => { active = false; window.clearTimeout(timer) }
  }, [sessionId])

  if (unavailable) return <StatusCard title="AI-assisted feedback" message="Feedback is temporarily unavailable. Your submitted response remains safely stored." />
  if (!feedback || ['queued', 'running', 'not_requested'].includes(feedback.status)) {
    return <StatusCard loading title="AI-assisted feedback is being prepared" message="A versioned evaluator is reviewing this attempt. You can leave this page and return later." />
  }
  if (feedback.status === 'failed' || !feedback.assessment) {
    return <StatusCard title="AI-assisted feedback" message="The evaluator could not complete this attempt. Use the guided self-review above; no score was fabricated." />
  }

  const assessment = feedback.assessment
  return (
    <section aria-labelledby="ai-feedback-title" className="space-y-4">
      <Card className="overflow-hidden p-0">
        <div className="bg-brand px-5 py-6 text-white">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-accent-soft"><Bot size={17} /> AI-assisted practice estimate</p>
          <h2 id="ai-feedback-title" className="mt-2 text-2xl font-bold">Estimated range: {assessment.estimated_level_low}–{assessment.estimated_level_high}</h2>
          <p className="mt-2 text-sm text-white/80">Confidence: {assessment.confidence} · {assessment.overall_summary}</p>
        </div>
        <p className="flex items-start gap-2 p-4 text-sm text-muted"><ShieldCheck className="mt-0.5 shrink-0 text-good" size={18} /> {assessment.disclaimer}</p>
      </Card>
      <div className="grid gap-4 md:grid-cols-2">
        {assessment.dimensions.map((dimension) => (
          <Card key={dimension.key} className="p-5">
            <div className="flex items-center justify-between gap-3"><h3 className="font-bold text-ink">{DIMENSION_LABELS[dimension.key] ?? dimension.key}</h3><span className="rounded-full bg-brand-soft px-3 py-1 text-xs font-bold text-brand">{dimension.rating}/4</span></div>
            <p className="mt-3 text-sm leading-6 text-muted"><strong className="text-ink">Evidence:</strong> {dimension.evidence}</p>
            <p className="mt-2 text-sm leading-6 text-muted"><strong className="text-ink">Next step:</strong> {dimension.next_step}</p>
          </Card>
        ))}
      </div>
      {feedback.transcript && <details className="card p-5"><summary className="cursor-pointer font-bold text-ink">AI transcript used for feedback</summary><p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-muted">{feedback.transcript}</p></details>}
      {feedback.audit && <details className="text-xs text-muted"><summary className="cursor-pointer font-semibold">Feedback audit details</summary><p className="mt-2">Provider: {feedback.audit.provider} · Model: {feedback.audit.model} · Prompt: {feedback.audit.prompt_version}</p></details>}
    </section>
  )
}

function StatusCard({ title, message, loading = false }: { title: string; message: string; loading?: boolean }) {
  return <Card className="border-dashed p-5" aria-live="polite"><h2 className="flex items-center gap-2 text-xl font-bold text-ink">{loading ? <Loader2 className="animate-spin text-brand" size={21} /> : <Bot size={21} />}{title}</h2><p className="mt-2 text-sm leading-6 text-muted">{message}</p></Card>
}
