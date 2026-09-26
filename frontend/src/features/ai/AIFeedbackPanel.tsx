import { Bot, CheckCircle2, Loader2, MessageCircleQuestion, RotateCcw, ShieldCheck, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Card } from '../../components/ui'
import { api } from '../../lib/api'
import { Link } from 'react-router-dom'
import { DIMENSION_LABELS } from './dimensionLabels'
import { AICoachTrigger } from '../coach/AICoachProvider'

type Dimension = { key: string; rating: number; evidence: string; next_step: string }
type LevelTwelveExemplar = {
  response: string
  why_it_is_strong: string
  highlights: { excerpt: string; why_it_matters: string }[]
  verified_level_low?: number
  verified_level_high?: number
  /** Where each answer-pattern step begins, as a verbatim excerpt. */
  pattern_map?: { step: string; excerpt: string }[]
}
type PatternCheck = { step: string; followed: boolean; note: string }
type FeedbackState = {
  status: 'not_requested' | 'queued' | 'running' | 'succeeded' | 'failed'
  kind?: 'writing_feedback' | 'speaking_feedback'
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
    pattern_check?: PatternCheck[]
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
  const [refreshKey, setRefreshKey] = useState(0)
  const [retryingExample, setRetryingExample] = useState(false)
  const [retryError, setRetryError] = useState('')

  useEffect(() => {
    let active = true
    let timer = 0
    let pending = false
    const load = async () => {
      window.clearTimeout(timer)
      try {
        const result = await api.get<FeedbackState>(`/sessions/${sessionId}/ai-feedback/`, tokenHeaders(sessionId))
        if (!active) return
        setFeedback(result)
        setUnavailable(false)
        // The assessment and the model-answer exemplar are separate jobs. The
        // assessment can be ready while the exemplar is still being generated;
        // keep polling in that state so the answer appears here without the
        // learner having to leave for the dashboard and come back.
        const assessmentPending = result.status === 'queued' || result.status === 'running'
        const exemplarPending = result.example_status === 'queued' || result.example_status === 'running'
        pending = assessmentPending || exemplarPending
        if (pending) timer = window.setTimeout(() => void load(), 3000)
      } catch {
        if (active) setUnavailable(true)
      }
    }
    void load()
    // A backgrounded tab (e.g. switching apps while grading runs) can have its
    // poll timer throttled well past its delay; polling immediately when the
    // tab regains focus keeps a nearly ready result from feeling stuck.
    const onVisible = () => {
      if (pending && document.visibilityState === 'visible') void load()
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      active = false
      window.clearTimeout(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [sessionId, refreshKey])

  const retryExample = async () => {
    setRetryingExample(true)
    setRetryError('')
    try {
      const result = await api.post<FeedbackState>(`/sessions/${sessionId}/ai-feedback/`, undefined, tokenHeaders(sessionId))
      setFeedback(result)
      setUnavailable(false)
      setRefreshKey((value) => value + 1)
    } catch (reason: unknown) {
      setRetryError(reason instanceof Error ? reason.message : 'Could not restart the example answer.')
    } finally {
      setRetryingExample(false)
    }
  }

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
  const coachSkill = feedback.kind === 'speaking_feedback'
    ? 'speaking'
    : feedback.kind === 'writing_feedback'
      ? 'writing'
      : ''
  const coachPrompt = `Help me improve the priorities from my ${coachSkill || 'practice'} feedback: ${assessment.priorities.join('; ')}`
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
      {assessment.pattern_check && assessment.pattern_check.length > 0 && <PatternCheckCard checks={assessment.pattern_check} />}
      {feedback.transcript && <details className="card p-5"><summary className="cursor-pointer font-bold text-ink">AI transcript used for feedback</summary><p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-muted">{feedback.transcript}</p></details>}
      {assessment.level_twelve_exemplar && <LevelTwelveExemplarPanel exemplar={assessment.level_twelve_exemplar} spoken={feedback.kind === 'speaking_feedback'} />}
      <Card className="border-brand/20 bg-brand-soft/35">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-bold text-ink">Need to understand this feedback?</p>
            <p className="mt-1 text-sm leading-6 text-muted">Ask a direct follow-up and get a next step without waiting for another evaluation.</p>
          </div>
          <AICoachTrigger
            skill={coachSkill === 'speaking' || coachSkill === 'writing' ? coachSkill : 'general'}
            prompt={coachPrompt}
            className="inline-flex min-h-10 shrink-0 items-center justify-center gap-2 rounded-full bg-brand px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
          >
            <MessageCircleQuestion size={17} /> Ask AI Coach
          </AICoachTrigger>
        </div>
      </Card>
      {['queued', 'running'].includes(feedback.example_status ?? '') && <Card className="border-dashed p-4 text-sm text-muted" aria-live="polite"><Loader2 className="mr-2 inline animate-spin text-brand" size={16} />Preparing your example high-scoring answer…</Card>}
      {feedback.example_status === 'failed' && (
        <Card className="border-dashed p-4 text-sm text-muted">
          <p>Your score is ready. The example answer could not be generated after several attempts.</p>
          <button type="button" onClick={() => void retryExample()} disabled={retryingExample} className="mt-3 inline-flex min-h-10 items-center gap-2 rounded-full border border-brand px-4 py-2 text-sm font-semibold text-brand transition hover:bg-brand-soft disabled:cursor-not-allowed disabled:opacity-60">
            {retryingExample ? <Loader2 className="animate-spin" size={16} /> : <RotateCcw size={16} />}
            {retryingExample ? 'Trying again…' : 'Try again'}
          </button>
          {retryError && <p role="alert" className="mt-2 text-bad">{retryError}</p>}
        </Card>
      )}
      {practiceHref && <Card className="border-accent/30 bg-accent-soft/25"><p className="text-sm font-bold text-ink">Apply this feedback on a fresh prompt</p><p className="mt-1 text-sm text-muted">Try the same task type again so the app can compare your next response with this one.</p><Link to={practiceHref} className="mt-3 inline-flex min-h-10 items-center rounded-full bg-brand px-4 py-2 text-sm font-semibold text-white">Practise this next</Link></Card>}
      {feedback.audit && <details className="text-xs text-muted"><summary className="cursor-pointer font-semibold">Feedback audit details</summary><p className="mt-2">Provider: {feedback.audit.provider} · Model: {feedback.audit.model} · Prompt: {feedback.audit.prompt_version}</p></details>}
    </section>
  )
}

function LevelTwelveExemplarPanel({ exemplar, spoken }: { exemplar: LevelTwelveExemplar; spoken: boolean }) {
  return (
    <Card className="border-accent/40 bg-accent-soft/20 p-5">
      <p className="text-xs font-bold uppercase tracking-widest text-brand">Score-12 learning model</p>
      <h3 className="mt-1 text-xl font-bold text-ink">How the AI would answer this task</h3>
      <p className="mt-2 text-sm leading-6 text-muted">{exemplar.why_it_is_strong}</p>
      {exemplar.verified_level_low !== undefined && (
        <p className="mt-2 text-sm font-semibold text-ink">
          <ShieldCheck className="mr-1 inline text-brand" size={16} />
          Checked by the same AI grader: {exemplar.verified_level_low}–{exemplar.verified_level_high}
          {spoken && <span className="font-normal text-muted"> as a transcript. Your spoken score also depends on pace and clarity, so read it at a natural pace.</span>}
        </p>
      )}
      <div className="mt-4 rounded-lg bg-surface p-4 text-sm leading-7 text-ink">
        <p className="whitespace-pre-wrap">
          {stepSegments(exemplar.response, exemplar.pattern_map ?? []).map((segment, index) => (
            <span key={index}>
              {segment.step && <span className="mr-1 rounded-full bg-accent-soft px-2 py-0.5 text-xs font-bold text-ink">{segment.step}</span>}
              {segment.text}
            </span>
          ))}
        </p>
      </div>
      <div className="mt-4 space-y-2">
        <p className="text-sm font-bold text-ink">Why this response is strong</p>
        {exemplar.highlights.map((highlight, index) => (
          <div key={`${highlight.excerpt}-${index}`} className="rounded-lg border border-accent/30 bg-surface-secondary p-3 text-sm leading-6 text-muted">
            <mark className="rounded bg-accent-soft px-1 font-semibold text-ink">“{highlight.excerpt}”</mark>
            <span> — {highlight.why_it_matters}</span>
          </div>
        ))}
      </div>
    </Card>
  )
}

function PatternCheckCard({ checks }: { checks: PatternCheck[] }) {
  const followed = checks.filter((check) => check.followed).length
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-bold text-ink">Answer pattern check</h3>
        <span className="rounded-full bg-brand-soft px-3 py-1 text-xs font-bold text-brand">{followed}/{checks.length} steps</span>
      </div>
      <ul className="mt-3 space-y-2">
        {checks.map((check) => (
          <li key={check.step} className="flex items-start gap-2 text-sm leading-6">
            {check.followed
              ? <CheckCircle2 size={17} className="mt-0.5 shrink-0 text-good" aria-label="Followed" />
              : <XCircle size={17} className="mt-0.5 shrink-0 text-bad" aria-label="Missing" />}
            <span><strong className="text-ink">{check.step}</strong> <span className="text-muted">— {check.note}</span></span>
          </li>
        ))}
      </ul>
    </Card>
  )
}

/** Split an example answer where each pattern step begins, so steps can be labeled. */
function stepSegments(response: string, map: { step: string; excerpt: string }[]): { step?: string; text: string }[] {
  const starts: { step: string; index: number }[] = []
  let from = 0
  for (const entry of map) {
    const index = response.indexOf(entry.excerpt, from)
    if (index < 0) continue
    starts.push({ step: entry.step, index })
    from = index + entry.excerpt.length
  }
  if (starts.length === 0) return [{ text: response }]
  const segments: { step?: string; text: string }[] = []
  if (starts[0].index > 0) segments.push({ text: response.slice(0, starts[0].index) })
  starts.forEach((start, position) => {
    const end = starts[position + 1]?.index ?? response.length
    segments.push({ step: start.step, text: response.slice(start.index, end) })
  })
  return segments
}

function StatusCard({ title, message, loading = false }: { title: string; message: string; loading?: boolean }) {
  return <Card className="border-dashed p-5" aria-live="polite"><h2 className="flex items-center gap-2 text-xl font-bold text-ink">{loading ? <Loader2 className="animate-spin text-brand" size={21} /> : <Bot size={21} />}{title}</h2><p className="mt-2 text-sm leading-6 text-muted">{message}</p></Card>
}
