import { ArrowLeft, ArrowRight, CheckCircle2, Clock3, Flag, Save, XCircle } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { Button, Card, Meter } from '../../components/ui'
import { ApiError, api } from '../../lib/api'
import type {
  LearningFeedback,
  ReadingSession,
  SaveResult,
  SessionResult,
} from './types'

type LocationState = { session?: ReadingSession }

function tokenHeaders(sessionId: string): Record<string, string> {
  const token = sessionStorage.getItem(`celpip-guest-${sessionId}`)
  return token ? { 'X-Guest-Token': token } : {}
}

export function ReadingSessionPage() {
  const { sessionId = '' } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const initial = (location.state as LocationState | null)?.session
  const [session, setSession] = useState<ReadingSession | null>(initial ?? null)
  const [result, setResult] = useState<SessionResult | null>(null)
  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)
  const [feedback, setFeedback] = useState<LearningFeedback | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (initial || !sessionId) return
    api.get<ReadingSession>(`/sessions/${sessionId}/`, tokenHeaders(sessionId))
      .then((loaded) => {
        setSession(loaded)
        const unanswered = loaded.content.questions.findIndex(
          (question) => !loaded.responses.some((response) => response.question_id === question.id),
        )
        setIndex(unanswered >= 0 ? unanswered : 0)
        if (loaded.state === 'submitted') {
          return api.get<SessionResult>(`/sessions/${sessionId}/results/`, tokenHeaders(sessionId))
        }
      })
      .then((loadedResult) => loadedResult && setResult(loadedResult))
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Could not resume this session.'))
  }, [initial, sessionId])

  const question = session?.content.questions[index]
  const existing = useMemo(
    () => session?.responses.find((response) => response.question_id === question?.id),
    [session, question],
  )

  useEffect(() => {
    const response = session?.responses.find(
      (candidate) => candidate.question_id === question?.id,
    )
    setSelected(response?.selected_choice_id ?? null)
    setFeedback(null)
  }, [index, question?.id])

  async function saveAnswer() {
    if (!session || !question || selected === null) return
    setSaving(true)
    setError('')
    try {
      const saved = await api.put<SaveResult>(
        `/sessions/${session.id}/responses/${question.id}/`,
        { selected_choice_id: selected, expected_revision: existing?.revision ?? 0 },
        { ...tokenHeaders(session.id), 'Idempotency-Key': crypto.randomUUID() },
      )
      setSession((current) => {
        if (!current) return current
        return {
          ...current,
          responses: [
            ...current.responses.filter((response) => response.question_id !== question.id),
            saved,
          ],
        }
      })
      if (saved.feedback) {
        setFeedback(saved.feedback)
      } else if (index < session.content.questions.length - 1) {
        setIndex((current) => current + 1)
      }
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Your answer could not be saved.')
    } finally {
      setSaving(false)
    }
  }

  async function submit() {
    if (!session) return
    setSaving(true)
    setError('')
    try {
      const scored = await api.post<SessionResult>(
        `/sessions/${session.id}/submit/`,
        undefined,
        tokenHeaders(session.id),
      )
      setResult(scored)
      setSession((current) => current ? { ...current, state: 'submitted' } : current)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'This session could not be submitted.')
    } finally {
      setSaving(false)
    }
  }

  if (error && !session) {
    return <SessionError message={error} onBack={() => navigate('/practice')} />
  }
  if (!session || !question) {
    return <p role="status" className="py-16 text-center text-muted">Loading your Reading session…</p>
  }
  if (result) {
    return <Results session={session} result={result} />
  }

  const answeredCount = session.responses.filter((response) => response.selected_choice_id).length
  const isLast = index === session.content.questions.length - 1
  return (
    <div className="mx-auto w-full max-w-7xl animate-fade-in">
      <header className="mb-4 flex flex-wrap items-center gap-3 rounded-card border border-line bg-surface px-4 py-3 shadow-card">
        <Button variant="ghost" onClick={() => navigate(session.mode === 'learn' ? '/learn' : '/practice')}>
          <ArrowLeft size={17} /> Exit
        </Button>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase tracking-wider text-accent">
            Reading · {session.mode === 'learn' ? 'Learn mode' : 'Timed practice'}
          </p>
          <h1 className="truncate font-bold text-ink">{session.content.title}</h1>
        </div>
        {session.deadline_at && <SessionTimer deadline={session.deadline_at} serverNow={session.server_now} />}
        <span className="text-sm font-semibold text-muted">{answeredCount}/{session.content.questions.length} saved</span>
      </header>

      <Meter
        value={index + 1}
        max={session.content.questions.length}
        label={`Question ${index + 1} of ${session.content.questions.length}`}
      />

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(22rem,0.85fr)]">
        <Card className="max-h-[calc(100vh-12rem)] overflow-y-auto p-5 sm:p-7">
          <p className="eyebrow">Source material</p>
          <p className="mt-2 text-sm font-medium text-muted">{session.content.instructions}</p>
          <div className="mt-5"><Stimulus stimulus={session.content.stimulus} /></div>
          {session.content.learning_notes && (
            <aside className="mt-6 rounded-input border border-info/30 bg-info-bg p-4 text-sm text-ink">
              <strong>Learning note:</strong> {session.content.learning_notes}
            </aside>
          )}
        </Card>

        <Card className="self-start p-5 sm:p-7">
          <form onSubmit={(event) => { event.preventDefault(); void saveAnswer() }}>
            <fieldset disabled={saving}>
              <legend className="text-lg font-bold leading-7 text-ink">
                <span className="mb-2 block text-xs font-bold uppercase tracking-wider text-accent">
                  {question.skill_focus.replace('_', ' ')}
                </span>
                {question.order}. {question.stem}
              </legend>
              <div className="mt-5 space-y-3">
                {question.choices.map((choice) => {
                  const checked = selected === choice.id
                  const correct = feedback?.correct_choice_id === choice.id
                  return (
                    <label
                      key={choice.id}
                      className={`flex min-h-12 cursor-pointer items-start gap-3 rounded-input border p-3 text-sm transition ${
                        correct ? 'border-good bg-good-soft' : checked ? 'border-brand bg-brand-soft' : 'border-line bg-surface hover:border-brand'
                      }`}
                    >
                      <input
                        type="radio"
                        name={`question-${question.id}`}
                        value={choice.id}
                        checked={checked}
                        onChange={() => setSelected(choice.id)}
                        className="mt-0.5 h-5 w-5 accent-brand"
                      />
                      <span className="leading-5 text-ink">{choice.text}</span>
                    </label>
                  )
                })}
              </div>
            </fieldset>

            {feedback && (
              <div role="status" className={`mt-5 rounded-input p-4 ${feedback.is_correct ? 'bg-good-soft' : 'bg-bad-soft'}`}>
                <p className={`flex items-center gap-2 font-bold ${feedback.is_correct ? 'text-good' : 'text-bad'}`}>
                  {feedback.is_correct ? <CheckCircle2 size={20} /> : <XCircle size={20} />}
                  {feedback.is_correct ? 'Correct' : 'Not quite'}
                </p>
                <p className="mt-2 text-sm leading-6 text-ink">{feedback.selected_choice_explanation}</p>
                <p className="mt-2 text-sm leading-6 text-muted"><strong>Evidence:</strong> {feedback.evidence}</p>
              </div>
            )}

            {error && <p role="alert" className="mt-4 rounded-input bg-bad-soft p-3 text-sm text-bad">{error}</p>}
            <div className="mt-6 flex flex-wrap justify-between gap-2">
              <Button type="button" variant="secondary" disabled={index === 0 || saving} onClick={() => setIndex((value) => value - 1)}>
                <ArrowLeft size={17} /> Previous
              </Button>
              {feedback ? (
                isLast ? (
                  <Button type="button" onClick={() => void submit()} disabled={saving}>
                    <Flag size={17} /> See results
                  </Button>
                ) : (
                  <Button type="button" onClick={() => setIndex((value) => value + 1)}>
                    Next <ArrowRight size={17} />
                  </Button>
                )
              ) : (
                <Button type="submit" disabled={selected === null || saving}>
                  <Save size={17} /> {saving ? 'Saving…' : isLast && session.mode === 'practice' ? 'Save answer' : 'Save & continue'}
                </Button>
              )}
            </div>
            {session.mode === 'practice' && isLast && answeredCount === session.content.questions.length && (
              <Button type="button" variant="accent" className="mt-3 w-full" onClick={() => void submit()} disabled={saving}>
                <Flag size={17} /> Submit practice
              </Button>
            )}
          </form>
        </Card>
      </div>
    </div>
  )
}

function SessionTimer({ deadline, serverNow }: { deadline: string; serverNow: string }) {
  const clockOffset = useMemo(() => Date.now() - new Date(serverNow).getTime(), [serverNow])
  const [seconds, setSeconds] = useState(() => Math.max(0, Math.ceil((new Date(deadline).getTime() - (Date.now() - clockOffset)) / 1000)))
  useEffect(() => {
    const tick = () => setSeconds(Math.max(0, Math.ceil((new Date(deadline).getTime() - (Date.now() - clockOffset)) / 1000)))
    const timer = window.setInterval(tick, 1000)
    return () => window.clearInterval(timer)
  }, [deadline, clockOffset])
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60
  const announcement = seconds === 300 ? 'Five minutes remaining' : seconds === 60 ? 'One minute remaining' : seconds === 0 ? 'Time has ended' : ''
  return (
    <div className={`inline-flex items-center gap-2 rounded-full px-3 py-2 text-sm font-bold tabular-nums ${seconds <= 60 ? 'bg-bad-soft text-bad' : 'bg-brand-soft text-brand'}`}>
      <Clock3 size={17} aria-hidden="true" />
      <span aria-label={`${minutes} minutes ${remainder} seconds remaining`}>{minutes}:{String(remainder).padStart(2, '0')}</span>
      <span className="sr-only" aria-live="polite">{announcement}</span>
    </div>
  )
}

function Stimulus({ stimulus }: { stimulus: Record<string, unknown> }) {
  const type = String(stimulus.type ?? '')
  if (type === 'email') {
    return (
      <article className="overflow-hidden rounded-input border border-line bg-surface">
        <dl className="grid grid-cols-[4rem_1fr] gap-x-2 gap-y-1 border-b border-line bg-surface-secondary p-4 text-sm">
          <dt className="font-bold text-muted">From</dt><dd>{String(stimulus.from)}</dd>
          <dt className="font-bold text-muted">To</dt><dd>{String(stimulus.to)}</dd>
          <dt className="font-bold text-muted">Subject</dt><dd className="font-semibold">{String(stimulus.subject)}</dd>
        </dl>
        <p className="whitespace-pre-line p-5 text-sm leading-7 text-ink">{String(stimulus.body)}</p>
      </article>
    )
  }
  if (type === 'table') {
    const columns = stimulus.columns as string[]
    const rows = stimulus.rows as string[][]
    return (
      <div>
        <h2 className="mb-3 text-xl font-bold text-ink">{String(stimulus.title)}</h2>
        <div className="overflow-x-auto rounded-input border border-line">
          <table className="w-full min-w-[42rem] border-collapse text-left text-sm">
            <thead className="bg-brand text-white"><tr>{columns.map((column) => <th key={column} className="p-3">{column}</th>)}</tr></thead>
            <tbody>{rows.map((row, rowIndex) => <tr key={rowIndex} className="border-t border-line">{row.map((cell, cellIndex) => <td key={cellIndex} className="p-3 align-top">{cell}</td>)}</tr>)}</tbody>
          </table>
        </div>
        <p className="mt-3 text-sm leading-6 text-muted">{String(stimulus.notes)}</p>
      </div>
    )
  }
  if (type === 'article') {
    const sections = stimulus.sections as Array<{ heading: string; body: string }>
    return <article><h2 className="text-xl font-bold text-ink">{String(stimulus.title)}</h2>{sections.map((section) => <section key={section.heading} className="mt-5"><h3 className="font-bold text-ink">{section.heading}</h3><p className="mt-1 text-sm leading-7 text-ink">{section.body}</p></section>)}</article>
  }
  if (type === 'viewpoints') {
    const speakers = stimulus.speakers as Array<{ name: string; position: string; body: string }>
    return <article><h2 className="text-xl font-bold text-ink">{String(stimulus.title)}</h2><p className="mt-2 text-sm leading-7 text-muted">{String(stimulus.background)}</p><div className="mt-5 space-y-4">{speakers.map((speaker) => <section key={speaker.name} className="rounded-input border border-line p-4"><h3 className="font-bold text-ink">{speaker.name}</h3><p className="text-xs font-semibold uppercase tracking-wide text-accent">{speaker.position}</p><p className="mt-2 text-sm leading-7 text-ink">{speaker.body}</p></section>)}</div></article>
  }
  return <pre className="whitespace-pre-wrap text-sm">{JSON.stringify(stimulus, null, 2)}</pre>
}

function Results({ session, result }: { session: ReadingSession; result: SessionResult }) {
  return (
    <div className="mx-auto max-w-4xl space-y-6 animate-fade-up">
      <Card className="overflow-hidden p-0 text-center">
        <div className="bg-brand px-5 py-8 text-white">
          <p className="text-xs font-bold uppercase tracking-widest text-accent-soft">{result.score_label}</p>
          <p className="mt-3 text-5xl font-bold tabular-nums">{result.raw_correct}/{result.raw_possible}</p>
          <p className="mt-2 text-lg font-semibold">{result.accuracy_percent}% correct</p>
        </div>
        <p className="p-4 text-sm text-muted">{result.disclaimer}</p>
      </Card>
      <section aria-labelledby="review-title">
        <h2 id="review-title" className="text-2xl font-bold text-ink">Review your answers</h2>
        <div className="mt-4 space-y-4">
          {session.content.questions.map((question) => {
            const outcome = result.outcomes.find((candidate) => candidate.question_id === question.id)!
            return (
              <Card key={question.id} className={outcome.is_correct ? 'border-good/40' : 'border-bad/40'}>
                <h3 className="font-bold text-ink">{question.order}. {question.stem}</h3>
                <p className={`mt-2 flex items-center gap-2 text-sm font-bold ${outcome.is_correct ? 'text-good' : 'text-bad'}`}>
                  {outcome.is_correct ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
                  {outcome.is_correct ? 'Correct' : outcome.selected_choice_id ? 'Incorrect' : 'Not answered'}
                </p>
                <p className="mt-3 text-sm leading-6 text-ink">{outcome.explanation}</p>
                <p className="mt-2 rounded-input bg-surface-secondary p-3 text-sm leading-6 text-muted"><strong>Evidence:</strong> {outcome.evidence}</p>
              </Card>
            )
          })}
        </div>
      </section>
      <div className="flex flex-wrap gap-3">
        <ButtonLinkSafe to={session.mode === 'learn' ? '/learn' : '/practice'}>Choose another set</ButtonLinkSafe>
      </div>
    </div>
  )
}

function ButtonLinkSafe({ to, children }: { to: string; children: string }) {
  const navigate = useNavigate()
  return <Button onClick={() => navigate(to)}>{children}</Button>
}

function SessionError({ message, onBack }: { message: string; onBack: () => void }) {
  return <Card className="mx-auto max-w-xl text-center"><h1 className="text-2xl font-bold text-ink">Session unavailable</h1><p role="alert" className="mt-3 text-muted">{message}</p><Button className="mt-6" onClick={onBack}>Back to Practice</Button></Card>
}
