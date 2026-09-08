import { Bot, Loader2, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Card } from '../../components/ui'
import { api } from '../../lib/api'
import { Link } from 'react-router-dom'
import { DIMENSION_LABELS } from './dimensionLabels'

type Dimension = { key: string; rating: number; evidence: string; next_step: string }
type LevelTwelveExemplar = {
  response: string
  why_it_is_strong: string
  highlights: { excerpt: string; why_it_matters: string }[]
}
type FeedbackState = {
  status: 'not_requested' | 'queued' | 'running' | 'succeeded' | 'failed'
  error?: string
  example_status?: 'not_requested' | 'queued' | 'running' | 'succeeded' | 'failed'
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
    level_twelve_exemplar?: LevelTwelveExemplar
  }
  audit?: { provider: string; model: string; prompt_version: string; created_at: string }
}

function tokenHeaders(sessionId: string): Record<string, string> {
  const token = sessionStorage.getItem(`celpip-guest-${sessionId}`)
  return token ? { 'X-Guest-Token': token } : {}
}

export function AIFeedbackPanel({ sessionId, practiceHref }: { sessionId: string; practiceHref?: string }) {
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
  if (!feedback || ['queued', 'running'].includes(feedback.status)) {
    return <StatusCard loading title="AI-assisted feedback is being prepared" message="A versioned evaluator is reviewing this attempt. You can leave this page and return later." />
  }
  if (feedback.status === 'not_requested') {
    return <StatusCard title="AI-assisted feedback is unavailable" message="This submitted attempt was not placed in the analysis queue. Please refresh the page or contact support if it continues." />
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
      {assessment.level_twelve_exemplar && <LevelTwelveExemplarPanel exemplar={assessment.level_twelve_exemplar} />}
      {['queued', 'running'].includes(feedback.example_status ?? '') && <Card className="border-dashed p-4 text-sm text-muted" aria-live="polite"><Loader2 className="mr-2 inline animate-spin text-brand" size={16} />Preparing your example high-scoring answer…</Card>}
      {feedback.example_status === 'failed' && <Card className="border-dashed p-4 text-sm text-muted">Your score is ready. The example answer could not be generated after several attempts.</Card>}
      {practiceHref && <Card className="border-accent/30 bg-accent-soft/25"><p className="text-sm font-bold text-ink">Apply this feedback on a fresh prompt</p><p className="mt-1 text-sm text-muted">Try the same task type again so the app can compare your next response with this one.</p><Link to={practiceHref} className="mt-3 inline-flex min-h-10 items-center rounded-full bg-brand px-4 py-2 text-sm font-semibold text-white">Practise this next</Link></Card>}
      {feedback.audit && <details className="text-xs text-muted"><summary className="cursor-pointer font-semibold">Feedback audit details</summary><p className="mt-2">Provider: {feedback.audit.provider} · Model: {feedback.audit.model} · Prompt: {feedback.audit.prompt_version}</p></details>}
    </section>
  )
}

function LevelTwelveExemplarPanel({ exemplar }: { exemplar: LevelTwelveExemplar }) {
  return (
    <Card className="border-accent/40 bg-accent-soft/20 p-5">
      <p className="text-xs font-bold uppercase tracking-widest text-brand">Score-12 learning model</p>
      <h3 className="mt-1 text-xl font-bold text-ink">How the AI would answer this task</h3>
      <p className="mt-2 text-sm leading-6 text-muted">{exemplar.why_it_is_strong}</p>
      <div className="mt-4 rounded-lg bg-white/70 p-4 text-sm leading-7 text-ink">
        <p className="whitespace-pre-wrap">{exemplar.response}</p>
      </div>
      <div className="mt-4 space-y-2">
        <p className="text-sm font-bold text-ink">Why this response is strong</p>
        {exemplar.highlights.map((highlight, index) => (
          <div key={`${highlight.excerpt}-${index}`} className="rounded-lg border border-accent/30 bg-white/60 p-3 text-sm leading-6 text-muted">
            <mark className="rounded bg-accent-soft px-1 font-semibold text-ink">“{highlight.excerpt}”</mark>
            <span> — {highlight.why_it_matters}</span>
          </div>
        ))}
      </div>
    </Card>
  )
}

function StatusCard({ title, message, loading = false }: { title: string; message: string; loading?: boolean }) {
  return <Card className="border-dashed p-5" aria-live="polite"><h2 className="flex items-center gap-2 text-xl font-bold text-ink">{loading ? <Loader2 className="animate-spin text-brand" size={21} /> : <Bot size={21} />}{title}</h2><p className="mt-2 text-sm leading-6 text-muted">{message}</p></Card>
}
