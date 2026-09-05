import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Cloud,
  CloudOff,
  Flag,
  Loader2,
  Mail,
  RotateCcw,
  ScrollText,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { ApiError, api } from '../../lib/api'
import { AIFeedbackPanel } from '../ai/AIFeedbackPanel'
import { ReportContentIssue } from '../content/ReportContentIssue'
import { advanceMock } from '../mocks/api'
import { MockReturnNotice } from '../mocks/MockReturnNotice'
import { StudyTaskAction } from '../learning/StudyTaskAction'
import { countWords, targetState } from './wordCount'
import type {
  WritingReview,
  WritingSaveResult,
  WritingSession,
  WritingStimulus,
  WritingSubmitResponse,
} from './types'

type SaveStatus = 'idle' | 'saving' | 'saved' | 'unsaved' | 'error'

const AUTOSAVE_DELAY_MS = 900
const RETRY_DELAY_MS = 3000

function tokenHeaders(sessionId: string): Record<string, string> {
  const token = sessionStorage.getItem(`celpip-guest-${sessionId}`)
  return token ? { 'X-Guest-Token': token } : {}
}

export function WritingSessionPage() {
  const { sessionId = '' } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const studyTaskId = new URLSearchParams(location.search).get('study_task')

  const [session, setSession] = useState<WritingSession | null>(null)
  const [text, setText] = useState('')
  const [status, setStatus] = useState<SaveStatus>('idle')
  const [savedAt, setSavedAt] = useState<string | null>(null)
  const [loadError, setLoadError] = useState('')
  const [saveError, setSaveError] = useState('')
  const [deadlinePassed, setDeadlinePassed] = useState(false)
  const [submittedState, setSubmittedState] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [confirmingSubmit, setConfirmingSubmit] = useState(false)
  const [review, setReview] = useState<WritingReview | null>(null)
  const [checklist, setChecklist] = useState<Record<string, boolean>>({})

  // Mutable refs keep the autosave loop free of stale closures and let it
  // serialize concurrent saves so a slow response can never clobber newer text.
  const revisionRef = useRef(0)
  const lastSavedRef = useRef('')
  const textRef = useRef('')
  const inFlightRef = useRef(false)
  const submittedRef = useRef(false)
  const currentSaveRef = useRef<Promise<boolean> | null>(null)
  const debounceRef = useRef<number | undefined>(undefined)
  const retryRef = useRef<number | undefined>(undefined)

  const writingPath = `/sessions/${sessionId}/writing/`

  // ── Load / resume ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!sessionId) return
    let active = true
    api
      .get<WritingSession>(writingPath, tokenHeaders(sessionId))
      .then((loaded) => {
        if (!active) return
        setSession(loaded)
        const draft = loaded.submission?.text ?? ''
        setText(draft)
        textRef.current = draft
        lastSavedRef.current = draft
        revisionRef.current = loaded.submission?.revision ?? 0
        setSavedAt(loaded.submission?.saved_at ?? null)
        if (loaded.state === 'submitted') {
          submittedRef.current = true
          setSubmittedState(true)
          if (loaded.review) setReview(loaded.review)
        }
        setStatus('idle')
      })
      .catch((reason: unknown) => {
        if (active) {
          setLoadError(reason instanceof Error ? reason.message : 'Could not open this writing session.')
        }
      })
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  // ── Autosave engine ──────────────────────────────────────────────────────
  const doOneSave = useCallback(async (): Promise<boolean> => {
    const textToSave = textRef.current
    const expected = revisionRef.current
    inFlightRef.current = true
    setStatus('saving')
    try {
      const result = await api.put<WritingSaveResult>(
        writingPath,
        { text: textToSave, expected_revision: expected },
        { ...tokenHeaders(sessionId), 'Idempotency-Key': crypto.randomUUID() },
      )
      revisionRef.current = result.revision
      lastSavedRef.current = textToSave
      setSavedAt(result.saved_at)
      setSaveError('')
      return true
    } catch (reason) {
      return await handleSaveError(reason)
    } finally {
      inFlightRef.current = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  const handleSaveError = useCallback(
    async (reason: unknown): Promise<boolean> => {
      if (reason instanceof ApiError) {
        if (reason.code === 'stale_revision' || reason.code === 'idempotency_conflict') {
          // Re-sync the revision from the server, then let the loop re-save the
          // learner's newest text with the correct expected_revision.
          try {
            const fresh = await api.get<WritingSession>(writingPath, tokenHeaders(sessionId))
            revisionRef.current = fresh.submission?.revision ?? revisionRef.current
            return true
          } catch {
            setStatus('error')
            setSaveError('Your draft is out of sync. Choose Retry to save again.')
            return false
          }
        }
        if (reason.code === 'session_not_active') {
          submittedRef.current = true
          setSubmittedState(true)
          setStatus('idle')
          setSaveError('This response was already submitted, so it can no longer be edited.')
          return false
        }
        if (reason.code === 'session_deadline_passed') {
          setDeadlinePassed(true)
          setStatus('error')
          setSaveError('Time is up. You can still submit what you have written.')
          return false
        }
        if (reason.code === 'session_access_denied' || reason.code === 'guest_access_expired') {
          setLoadError(reason.message)
          return false
        }
        setStatus('error')
        setSaveError(reason.message)
        return false
      }
      // Network / offline: keep the text, surface the state, and retry shortly.
      setStatus('error')
      setSaveError('You appear to be offline. Your writing is safe here and we will keep retrying.')
      scheduleRetry()
      return false
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sessionId],
  )

  const saveNow = useCallback((): Promise<boolean> => {
    window.clearTimeout(debounceRef.current)
    if (!currentSaveRef.current) {
      const loop = async (): Promise<boolean> => {
        while (!submittedRef.current && textRef.current !== lastSavedRef.current) {
          const ok = await doOneSave()
          if (!ok) return false
        }
        if (!submittedRef.current && textRef.current === lastSavedRef.current) {
          setStatus('saved')
        }
        return true
      }
      currentSaveRef.current = loop().finally(() => {
        currentSaveRef.current = null
      })
    }
    return currentSaveRef.current
  }, [doOneSave])

  const scheduleRetry = useCallback(() => {
    window.clearTimeout(retryRef.current)
    retryRef.current = window.setTimeout(() => void saveNow(), RETRY_DELAY_MS)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Retry immediately once the browser reports it is back online.
  useEffect(() => {
    const onOnline = () => {
      if (textRef.current !== lastSavedRef.current && !submittedRef.current) void saveNow()
    }
    window.addEventListener('online', onOnline)
    return () => window.removeEventListener('online', onOnline)
  }, [saveNow])

  // Clear timers on unmount so nothing fires after navigation.
  useEffect(
    () => () => {
      window.clearTimeout(debounceRef.current)
      window.clearTimeout(retryRef.current)
    },
    [],
  )

  function onTextChange(value: string) {
    setText(value)
    textRef.current = value
    if (submittedRef.current || deadlinePassed) return
    if (value === lastSavedRef.current) {
      setStatus(inFlightRef.current ? 'saving' : 'saved')
      return
    }
    setStatus('unsaved')
    window.clearTimeout(debounceRef.current)
    debounceRef.current = window.setTimeout(() => void saveNow(), AUTOSAVE_DELAY_MS)
  }

  // ── Submit ───────────────────────────────────────────────────────────────
  async function doSubmit() {
    setSubmitting(true)
    setSaveError('')
    window.clearTimeout(debounceRef.current)
    await saveNow() // best-effort flush; POST below atomically carries the latest text
    try {
      const result = await api.post<WritingSubmitResponse>(
        `${writingPath}submit/`,
        { text: textRef.current },
        tokenHeaders(sessionId),
      )
      if ('awaiting_mock_results' in result) {
        await advanceAndReturn(result.mock.attempt_id, result.mock.task_order)
        return
      }
      submittedRef.current = true
      setReview(result)
      setSubmittedState(true)
      setStatus('idle')
      setSession((current) =>
        current
          ? { ...current, state: 'submitted', submitted_at: new Date().toISOString(), submission: result.submission }
          : current,
      )
    } catch (reason) {
      if (reason instanceof ApiError) {
        setSaveError(
          reason.code === 'empty_response'
            ? 'Write a response before submitting.'
            : reason.message,
        )
      } else {
        setSaveError('Your response could not be submitted. Check your connection and try again.')
      }
    } finally {
      setSubmitting(false)
      setConfirmingSubmit(false)
    }
  }

  // Advance the parent mock after a neutral embargoed submit. The server treats
  // a repeated advance as an idempotent replay, and the workspace GET reconciles
  // any expiry, so a transient failure still navigates to a safe view.
  async function advanceAndReturn(attemptId: string, taskOrder: number) {
    try {
      await advanceMock(attemptId, taskOrder)
    } catch {
      // Fall through: the workspace reconciles server state on load.
    }
    navigate(`/mock/${attemptId}`)
  }

  const wordCount = useMemo(() => countWords(text), [text])

  if (loadError) {
    return <SessionError message={loadError} onBack={() => navigate('/practice/writing')} />
  }
  if (!session) {
    return <p role="status" className="py-16 text-center text-muted">Loading your writing session…</p>
  }

  const stimulus = session.content.stimulus
  const target = stimulus.target_words
  const range = targetState(wordCount, target.min, target.max)

  if (submittedState && review) {
    return <WritingReviewView session={session} review={review} text={text} onBack={() => navigate('/practice/writing')} />
  }
  if (submittedState && session.mock && !review) {
    return (
      <MockReturnNotice
        attemptId={session.mock.attempt_id}
        taskOrder={session.mock.task_order}
        returnUrl={session.mock.return_url}
      />
    )
  }

  const editingLocked = submittedState || deadlinePassed
  const isMock = session.mode === 'mock'
  const exitTo = isMock ? session.mock?.return_url ?? '/mock' : session.mode === 'learn' ? '/learn/writing' : '/practice/writing'

  return (
    <div className="mx-auto w-full max-w-7xl animate-fade-in">
      <header className="mb-4 flex flex-wrap items-center gap-3 rounded-card border border-line bg-surface px-4 py-3 shadow-card">
        <Button variant="ghost" onClick={() => navigate(exitTo)}>
          <ArrowLeft size={17} /> Exit
        </Button>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase tracking-wider text-accent">
            Writing · {isMock ? 'Mock component' : session.mode === 'learn' ? 'Learn mode' : session.mode === 'diagnostic' ? 'Baseline assessment' : 'Timed practice'}
          </p>
          <h1 className="truncate font-bold text-ink">{session.content.title}</h1>
        </div>
        {session.deadline_at && !editingLocked && (
          <SessionTimer
            deadline={session.deadline_at}
            serverNow={session.server_now}
            onExpire={() => setDeadlinePassed(true)}
          />
        )}
        <SaveIndicator status={status} savedAt={savedAt} />
      </header>

      <div className="mb-4">
        <StudyTaskAction taskId={studyTaskId} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(24rem,1fr)]">
        <Card className="max-h-[calc(100vh-11rem)] overflow-y-auto p-5 sm:p-7">
          <PromptPanel stimulus={stimulus} instructions={session.content.instructions} />
          {session.content.learning_notes && (
            <aside className="mt-6 rounded-input border border-info/30 bg-info-bg p-4 text-sm text-ink">
              <strong>Learning note:</strong> {session.content.learning_notes}
            </aside>
          )}
        </Card>

        <Card className="self-start p-5 sm:p-7">
          <form onSubmit={(event) => event.preventDefault()}>
            <label htmlFor="writing-response" className="block text-sm font-bold text-ink">
              Your response
            </label>
            <p className="mt-1 text-xs text-muted">
              Aim for {target.min}–{target.max} words. Your draft saves automatically as you write.
            </p>
            <WritingChecklist
              requestedPoints={stimulus.requested_points}
              targetMin={target.min}
              targetMax={target.max}
              wordCount={wordCount}
              values={checklist}
              onChange={(key, checked) => setChecklist((current) => ({ ...current, [key]: checked }))}
            />
            <textarea
              id="writing-response"
              value={text}
              onChange={(event) => onTextChange(event.target.value)}
              disabled={editingLocked}
              spellCheck
              aria-describedby="writing-wordcount writing-save-status"
              className="mt-3 min-h-[22rem] w-full resize-y rounded-input border border-line bg-surface p-4 text-sm leading-7 text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand disabled:opacity-70"
              placeholder="Start writing your response here…"
            />

            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <p id="writing-wordcount" className={`text-sm font-semibold ${wordCountTone(range)}`}>
                <span className="tabular-nums">{wordCount}</span> {wordCount === 1 ? 'word' : 'words'}
                <span className="ml-2 font-normal text-muted">
                  {range === 'below' && `${target.min - wordCount} to reach the target`}
                  {range === 'within' && 'Within the 150–200 target'}
                  {range === 'above' && `${wordCount - target.max} over the target`}
                </span>
              </p>
            </div>

            {deadlinePassed && (
              <p role="status" className="mt-3 rounded-input bg-warn-soft p-3 text-sm text-ink">
                The suggested time has ended. You can still submit the response you have written.
              </p>
            )}
            {saveError && (
              <p role="alert" className="mt-3 flex items-start gap-2 rounded-input bg-bad-soft p-3 text-sm text-bad">
                <AlertTriangle size={16} className="mt-0.5 shrink-0" /> {saveError}
              </p>
            )}
            {status === 'error' && (
              <Button type="button" variant="secondary" className="mt-3" onClick={() => void saveNow()}>
                <RotateCcw size={16} /> Retry saving
              </Button>
            )}

            {confirmingSubmit ? (
              <div role="alertdialog" aria-label="Confirm submission" className="mt-6 rounded-input border border-warn/40 bg-warn-soft p-4">
                <p className="text-sm font-semibold text-ink">
                  Your response is {range === 'below' ? 'shorter' : 'longer'} than the 150–200 word target
                  ({wordCount} words). You can still submit, but submitting is final and cannot be changed.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button type="button" variant="accent" disabled={submitting} onClick={() => void doSubmit()}>
                    <Flag size={16} /> Submit anyway
                  </Button>
                  <Button type="button" variant="secondary" disabled={submitting} onClick={() => setConfirmingSubmit(false)}>
                    Keep writing
                  </Button>
                </div>
              </div>
            ) : (
              <Button
                type="button"
                className="mt-6 w-full"
                disabled={submitting || editingLocked}
                onClick={() => {
                  if (range !== 'within') setConfirmingSubmit(true)
                  else void doSubmit()
                }}
              >
                <Flag size={17} /> {submitting ? 'Submitting…' : 'Submit response'}
              </Button>
            )}
            <p className="mt-3 text-center text-xs text-muted">
              Submitting freezes your response for honest self-review. It is not an official CELPIP score.
            </p>
          </form>
        </Card>
      </div>
    </div>
  )
}

function WritingChecklist({
  requestedPoints,
  targetMin,
  targetMax,
  wordCount,
  values,
  onChange,
}: {
  requestedPoints: string[]
  targetMin: number
  targetMax: number
  wordCount: number
  values: Record<string, boolean>
  onChange: (key: string, checked: boolean) => void
}) {
  const checks = [
    ...requestedPoints.map((point, index) => ({ key: `point-${index}`, label: `Answered: ${point}` })),
    { key: 'clear-structure', label: 'My opening and main purpose are clear.' },
    { key: 'supporting-detail', label: 'I included specific supporting details.' },
    { key: 'tone', label: 'My tone matches the audience and situation.' },
    { key: 'edit', label: 'I checked grammar, spelling, and sentence clarity.' },
  ]
  const checkedCount = checks.filter((item) => values[item.key]).length
  const inRange = wordCount >= targetMin && wordCount <= targetMax
  return (
    <fieldset className="mt-4 rounded-input border border-line bg-surface-secondary/60 p-3">
      <legend className="px-1 text-xs font-bold uppercase tracking-wider text-muted">Before submitting</legend>
      <p className="mt-1 text-xs text-muted">Self-check your response; these reminders do not replace official scoring.</p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {checks.map((item) => (
          <label key={item.key} className="flex cursor-pointer items-start gap-2 rounded-input p-2 text-sm text-ink hover:bg-surface">
            <input
              type="checkbox"
              checked={Boolean(values[item.key])}
              onChange={(event) => onChange(item.key, event.target.checked)}
              className="mt-0.5 h-4 w-4 shrink-0 accent-brand"
            />
            <span>{item.label}</span>
          </label>
        ))}
      </div>
      <p className={`mt-2 text-xs font-semibold ${inRange ? 'text-good' : 'text-warn'}`}>
        {checkedCount}/{checks.length} checks complete · {inRange ? 'Word count is in range.' : `Aim for ${targetMin}–${targetMax} words.`}
      </p>
    </fieldset>
  )
}

function wordCountTone(range: 'below' | 'within' | 'above'): string {
  if (range === 'within') return 'text-good'
  return 'text-warn'
}

function SaveIndicator({ status, savedAt }: { status: SaveStatus; savedAt: string | null }) {
  const label =
    status === 'saving'
      ? 'Saving…'
      : status === 'unsaved'
        ? 'Unsaved changes'
        : status === 'error'
          ? 'Not saved'
          : savedAt
            ? 'Saved'
            : 'Ready'
  const Icon = status === 'saving' ? Loader2 : status === 'error' ? CloudOff : Cloud
  const tone =
    status === 'error'
      ? 'text-bad'
      : status === 'unsaved'
        ? 'text-warn'
        : status === 'saving'
          ? 'text-muted'
          : 'text-good'
  return (
    <span
      id="writing-save-status"
      role="status"
      aria-live="polite"
      className={`inline-flex items-center gap-1.5 text-sm font-semibold ${tone}`}
    >
      <Icon size={16} className={status === 'saving' ? 'animate-spin' : ''} aria-hidden="true" />
      {label}
    </span>
  )
}

function PromptPanel({ stimulus, instructions }: { stimulus: WritingStimulus; instructions: string }) {
  const isSurvey = stimulus.task_kind === 'survey'
  return (
    <div>
      <p className="eyebrow">{isSurvey ? 'Responding to survey questions' : 'Writing an email'}</p>
      <p className="mt-2 flex items-center gap-2 text-sm font-medium text-muted">
        {isSurvey ? <ScrollText size={16} className="text-accent" /> : <Mail size={16} className="text-accent" />}
        {instructions}
      </p>

      <div className="mt-5 rounded-input border border-line bg-surface-secondary p-4">
        <h2 className="text-sm font-bold text-ink">The situation</h2>
        <p className="mt-2 whitespace-pre-line text-sm leading-7 text-ink">{stimulus.scenario}</p>
        {stimulus.audience && (
          <p className="mt-3 text-xs font-semibold text-muted">Write to: {stimulus.audience}</p>
        )}
      </div>

      {isSurvey && stimulus.survey_question && (
        <div className="mt-5">
          <h2 className="text-sm font-bold text-ink">{stimulus.survey_question}</h2>
          <ul className="mt-2 space-y-2">
            {(stimulus.options ?? []).map((option) => (
              <li key={option.key} className="rounded-input border border-line bg-surface p-3 text-sm text-ink">
                {option.label}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-5">
        <h2 className="text-sm font-bold text-ink">Be sure to</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-muted">
          {stimulus.requested_points.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
      </div>

      {stimulus.guidance && stimulus.guidance.length > 0 && (
        <details className="mt-5 rounded-input border border-info/30 bg-info-bg p-4">
          <summary className="cursor-pointer text-sm font-bold text-ink focus-visible:outline-2 focus-visible:outline-brand">
            Tips for this prompt
          </summary>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-ink">
            {stimulus.guidance.map((tip) => (
              <li key={tip}>{tip}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}

function WritingReviewView({
  session,
  review,
  text,
  onBack,
}: {
  session: WritingSession
  review: WritingReview
  text: string
  onBack: () => void
}) {
  const submittedText = session.submission?.text ?? text
  const within = review.within_target
  return (
    <div className="mx-auto max-w-4xl space-y-6 animate-fade-up">
      <Card className="overflow-hidden p-0 text-center">
        <div className="bg-brand px-5 py-8 text-white">
          <p className="text-xs font-bold uppercase tracking-widest text-accent-soft">{review.score_label}</p>
          <p className="mt-3 flex items-center justify-center gap-2 text-4xl font-bold tabular-nums">
            <CheckCircle2 size={30} /> Submitted
          </p>
          <p className="mt-2 text-lg font-semibold">
            {review.word_count} words
            {within === true && ' · within the 150–200 target'}
            {within === false && ' · outside the 150–200 target'}
          </p>
        </div>
        <p className="p-4 text-sm text-muted">{review.disclaimer}</p>
      </Card>

      <section aria-labelledby="self-review-title">
        <h2 id="self-review-title" className="text-2xl font-bold text-ink">Guided self-review</h2>
        <p className="mt-1 text-sm text-muted">{review.rubric.note}</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {review.rubric.dimensions.map((dimension) => (
            <Card key={dimension.key} className="p-5">
              <h3 className="font-bold text-ink">{dimension.label}</h3>
              <p className="mt-2 text-sm leading-6 text-muted">{dimension.prompt}</p>
            </Card>
          ))}
        </div>
      </section>

      <section aria-labelledby="submitted-response-title">
        <h2 id="submitted-response-title" className="text-2xl font-bold text-ink">Your submitted response</h2>
        <Card className="mt-3 p-5">
          <p className="whitespace-pre-line text-sm leading-7 text-ink">{submittedText}</p>
        </Card>
      </section>

      <AIFeedbackPanel sessionId={session.id} practiceHref={`/practice/writing?task_type=${encodeURIComponent(session.content.task_type)}&exclude=${encodeURIComponent(session.content.slug)}`} />
      <ReportContentIssue sessionId={session.id} />

      <div className="flex flex-wrap gap-3">
        <Button onClick={onBack}>Choose another prompt</Button>
      </div>
    </div>
  )
}

function SessionTimer({
  deadline,
  serverNow,
  onExpire,
}: {
  deadline: string
  serverNow: string
  onExpire: () => void
}) {
  const clockOffset = useMemo(() => Date.now() - new Date(serverNow).getTime(), [serverNow])
  const compute = useCallback(
    () => Math.max(0, Math.ceil((new Date(deadline).getTime() - (Date.now() - clockOffset)) / 1000)),
    [deadline, clockOffset],
  )
  const [seconds, setSeconds] = useState(compute)
  const firedRef = useRef(false)
  useEffect(() => {
    const timer = window.setInterval(() => {
      const next = compute()
      setSeconds(next)
      if (next === 0 && !firedRef.current) {
        firedRef.current = true
        onExpire()
      }
    }, 1000)
    return () => window.clearInterval(timer)
  }, [compute, onExpire])
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60
  const announcement =
    seconds === 300 ? 'Five minutes remaining' : seconds === 60 ? 'One minute remaining' : seconds === 0 ? 'Time has ended' : ''
  return (
    <div className={`inline-flex items-center gap-2 rounded-full px-3 py-2 text-sm font-bold tabular-nums ${seconds <= 60 ? 'bg-bad-soft text-bad' : 'bg-brand-soft text-brand'}`}>
      <Clock3 size={17} aria-hidden="true" />
      <span aria-label={`${minutes} minutes ${remainder} seconds remaining`}>
        {minutes}:{String(remainder).padStart(2, '0')}
      </span>
      <span className="sr-only" aria-live="polite">{announcement}</span>
    </div>
  )
}

function SessionError({ message, onBack }: { message: string; onBack: () => void }) {
  return (
    <Card className="mx-auto max-w-xl text-center">
      <h1 className="text-2xl font-bold text-ink">Session unavailable</h1>
      <p role="alert" className="mt-3 text-muted">{message}</p>
      <Button className="mt-6" onClick={onBack}>Back to Writing practice</Button>
    </Card>
  )
}
