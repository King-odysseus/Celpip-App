import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Loader2,
  Mic2,
  RefreshCcw,
  ShieldCheck,
  Square,
  UploadCloud,
} from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, ButtonLink, Card } from '../../components/ui'
import { ApiError, api } from '../../lib/api'
import { AIFeedbackPanel } from '../ai/AIFeedbackPanel'
import { advanceMock } from '../mocks/api'
import { MockReturnNotice } from '../mocks/MockReturnNotice'
import { RetryAction } from './RetryAction'
import { SpeakingComparisonPanel } from './SpeakingComparisonPanel'
import { tokenHeaders } from './token'
import type {
  SpeakingRecording,
  SpeakingReview,
  SpeakingSaveResult,
  SpeakingSession,
  SpeakingStimulus,
  SpeakingSubmitResponse,
} from './types'

type RecorderPhase = 'ready' | 'preparing' | 'recording' | 'recorded' | 'uploading'

function preferredMimeType(): string | null {
  if (typeof MediaRecorder === 'undefined') return null
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg', 'audio/mp4']
  if (typeof MediaRecorder.isTypeSupported !== 'function') return 'audio/webm'
  return candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate)) ?? null
}

export function SpeakingSessionPage() {
  const { sessionId = '' } = useParams()
  const navigate = useNavigate()
  const [session, setSession] = useState<SpeakingSession | null>(null)
  const [phase, setPhase] = useState<RecorderPhase>('ready')
  const [remaining, setRemaining] = useState(0)
  const [recording, setRecording] = useState<SpeakingRecording | null>(null)
  const [review, setReview] = useState<SpeakingReview | null>(null)
  const [audioUrl, setAudioUrl] = useState('')
  const [error, setError] = useState('')
  const [loadError, setLoadError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const streamRef = useRef<MediaStream | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const recordingStartedRef = useRef(0)
  const recordedDurationRef = useRef(0)
  const localBlobRef = useRef<Blob | null>(null)
  const revisionRef = useRef(0)
  const objectUrlRef = useRef('')
  const mountedRef = useRef(true)
  const path = `/sessions/${sessionId}/speaking/`

  const replaceObjectUrl = useCallback((blob: Blob) => {
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
    const next = URL.createObjectURL(blob)
    objectUrlRef.current = next
    setAudioUrl(next)
  }, [])

  const loadPrivateAudio = useCallback(async (metadata: SpeakingRecording) => {
    try {
      const blob = await api.getBlob(metadata.audio_url, tokenHeaders(sessionId))
      if (mountedRef.current) replaceObjectUrl(blob)
    } catch (reason) {
      if (mountedRef.current) {
        setError(reason instanceof Error ? reason.message : 'Could not load your private recording.')
      }
    }
  }, [replaceObjectUrl, sessionId])

  useEffect(() => {
    mountedRef.current = true
    api
      .get<SpeakingSession>(path, tokenHeaders(sessionId))
      .then((loaded) => {
        if (!mountedRef.current) return
        setSession(loaded)
        if (loaded.submission) {
          setRecording(loaded.submission)
          revisionRef.current = loaded.submission.revision
          setPhase('recorded')
          void loadPrivateAudio(loaded.submission)
        }
        if (loaded.review) setReview(loaded.review)
      })
      .catch((reason: unknown) => {
        if (mountedRef.current) {
          setLoadError(reason instanceof Error ? reason.message : 'Could not open this Speaking session.')
        }
      })
    return () => {
      mountedRef.current = false
      if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
      streamRef.current?.getTracks().forEach((track) => track.stop())
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
    }
  }, [loadPrivateAudio, path, sessionId])

  const uploadBlob = useCallback(async (blob: Blob, durationMs: number) => {
    setPhase('uploading')
    setError('')
    const form = new FormData()
    const mime = blob.type || 'audio/webm'
    const extension = mime.includes('ogg') ? 'ogg' : mime.includes('mp4') ? 'mp4' : 'webm'
    form.append('audio', blob, `response.${extension}`)
    form.append('duration_ms', String(Math.max(100, Math.round(durationMs))))
    form.append('expected_revision', String(revisionRef.current))
    try {
      const saved = await api.put<SpeakingSaveResult>(path, form, {
        ...tokenHeaders(sessionId),
        'Idempotency-Key': crypto.randomUUID(),
      })
      if (!mountedRef.current) return
      revisionRef.current = saved.revision
      setRecording(saved)
      setPhase('recorded')
    } catch (reason) {
      if (!mountedRef.current) return
      setPhase('recorded')
      setError(
        reason instanceof ApiError
          ? reason.message
          : 'Your recording is still in this browser, but it could not be saved. Retry the upload.',
      )
    }
  }, [path, sessionId])

  const startRecording = useCallback(() => {
    const stream = streamRef.current
    const mimeType = preferredMimeType()
    if (!stream || !mimeType || !session) {
      setError('This browser cannot start a supported audio recording.')
      return
    }
    const recorder = new MediaRecorder(stream, { mimeType })
    recorderRef.current = recorder
    chunksRef.current = []
    recorder.ondataavailable = (event) => {
      if (event.data.size) chunksRef.current.push(event.data)
    }
    recorder.onstop = () => {
      const duration = Date.now() - recordingStartedRef.current
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType })
      stream.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      if (!mountedRef.current) return
      if (!blob.size) {
        setPhase('ready')
        setError('No audio was captured. Check your microphone and try again.')
        return
      }
      recordedDurationRef.current = duration
      localBlobRef.current = blob
      replaceObjectUrl(blob)
      void uploadBlob(blob, duration)
    }
    recorder.onerror = () => setError('The browser reported a microphone recording error.')
    recordingStartedRef.current = Date.now()
    recorder.start(250)
    setPhase('recording')
    setRemaining(session.content.stimulus.response_seconds)
  }, [replaceObjectUrl, session, uploadBlob])

  useEffect(() => {
    if (phase !== 'preparing' && phase !== 'recording') return
    const timer = window.setInterval(() => {
      setRemaining((current) => Math.max(0, current - 1))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [phase])

  useEffect(() => {
    if (remaining !== 0) return
    if (phase === 'preparing') startRecording()
    if (phase === 'recording' && recorderRef.current?.state === 'recording') {
      recorderRef.current.stop()
    }
  }, [phase, remaining, startRecording])

  async function begin() {
    setError('')
    if (!navigator.mediaDevices?.getUserMedia || !preferredMimeType()) {
      setError('Microphone recording is not supported in this browser. Try a current Chrome, Edge, Firefox, or Safari release.')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      })
      streamRef.current = stream
      setPhase('preparing')
      setRemaining(session?.content.stimulus.prep_seconds ?? 30)
    } catch {
      setError('Microphone permission was not granted. Allow microphone access in your browser, then try again.')
    }
  }

  function stopEarly() {
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
  }

  async function retryUpload() {
    if (!localBlobRef.current) return
    try {
      await uploadBlob(localBlobRef.current, recordedDurationRef.current)
    } catch {
      setError('The local recording could not be reopened. Please record again.')
    }
  }

  async function submit() {
    if (!recording || submitting) return
    setSubmitting(true)
    setError('')
    try {
      const result = await api.post<SpeakingSubmitResponse>(
        `${path}submit/`,
        undefined,
        tokenHeaders(sessionId),
      )
      if ('awaiting_mock_results' in result) {
        await advanceAndReturn(result.mock.attempt_id, result.mock.task_order)
        return
      }
      setReview(result)
      setRecording(result.submission)
      setSession((current) => current ? { ...current, state: 'submitted', submission: result.submission } : current)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not submit this recording.')
    } finally {
      setSubmitting(false)
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

  if (loadError) {
    return <SessionError message={loadError} onBack={() => navigate('/practice/speaking')} />
  }
  if (!session) {
    return <p role="status" className="py-16 text-center text-muted">Loading your Speaking session…</p>
  }
  if (review && recording) {
    return (
      <SpeakingReviewView
        session={session}
        review={review}
        recording={recording}
        audioUrl={audioUrl}
        onBack={() => navigate('/practice/speaking')}
      />
    )
  }
  if (session.state === 'submitted' && session.mock) {
    return (
      <MockReturnNotice
        attemptId={session.mock.attempt_id}
        taskOrder={session.mock.task_order}
        returnUrl={session.mock.return_url}
      />
    )
  }

  const stimulus = session.content.stimulus
  const timerLabel = phase === 'preparing' ? preparationLabel(stimulus, remaining) : 'Speaking time'
  const isMock = session.mode === 'mock'
  const exitTo = isMock ? session.mock?.return_url ?? '/mock' : session.mode === 'learn' ? '/learn/speaking' : '/practice/speaking'

  return (
    <div className="mx-auto w-full max-w-7xl animate-fade-in">
      <header className="mb-4 flex flex-wrap items-center gap-3 rounded-card border border-line bg-surface px-4 py-3 shadow-card">
        <Button variant="ghost" onClick={() => navigate(exitTo)}>
          <ArrowLeft size={17} /> Exit
        </Button>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase tracking-wider text-accent">
            Speaking · {isMock ? 'Mock component' : session.mode === 'learn' ? 'Learn mode' : 'Timed practice'}
          </p>
          <h1 className="flex flex-wrap items-center gap-2 truncate font-bold text-ink">
            <span className="truncate">{session.content.title}</span>
            <span className="rounded-full bg-brand-soft px-3 py-1 text-xs font-bold text-brand">
              Attempt {session.attempt.attempt_number}
            </span>
          </h1>
        </div>
        {(phase === 'preparing' || phase === 'recording') && (
          <Countdown label={timerLabel} seconds={remaining} recording={phase === 'recording'} />
        )}
      </header>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(22rem,.85fr)]">
        <Card className="p-5 sm:p-7">
          <Prompt stimulus={stimulus} />
          {session.content.learning_notes && (
            <aside className="mt-5 rounded-input border border-info/30 bg-info-bg p-4 text-sm text-ink">
              <strong>Learning note:</strong> {session.content.learning_notes}
            </aside>
          )}
        </Card>

        <Card className="self-start p-5 sm:p-7">
          <h2 className="text-xl font-bold text-ink">Private recorder</h2>
          <p className="mt-2 flex items-start gap-2 text-sm leading-6 text-muted">
            <ShieldCheck size={18} className="mt-0.5 shrink-0 text-good" />
            Your browser asks before using the microphone. Audio is uploaded privately only after recording stops.
          </p>

          {error && (
            <p role="alert" className="mt-4 flex items-start gap-2 rounded-input bg-bad-soft p-3 text-sm text-bad">
              <AlertTriangle size={17} className="mt-0.5 shrink-0" /> {error}
            </p>
          )}

          {phase === 'ready' && (
            <Button className="mt-6 w-full" onClick={() => void begin()}>
              <Mic2 size={18} /> Allow microphone and start preparation
            </Button>
          )}
          {phase === 'preparing' && (
            <div role="status" className="mt-6 rounded-card bg-brand-soft p-6 text-center text-brand">
              <Clock3 className="mx-auto" size={28} />
              <p className="mt-3 text-sm font-bold uppercase tracking-wider">{timerLabel}</p>
              <p className="mt-1 text-5xl font-bold tabular-nums">{remaining}</p>
              <p className="mt-2 text-sm">Recording starts automatically when preparation ends.</p>
            </div>
          )}
          {phase === 'recording' && (
            <div role="status" className="mt-6 rounded-card bg-bad-soft p-6 text-center text-bad">
              <span className="mx-auto block h-4 w-4 animate-pulse rounded-full bg-bad" />
              <p className="mt-3 text-sm font-bold uppercase tracking-wider">Recording</p>
              <p className="mt-1 text-5xl font-bold tabular-nums">{remaining}</p>
              <Button variant="secondary" className="mt-4" onClick={stopEarly}>
                <Square size={16} /> Stop early
              </Button>
            </div>
          )}
          {phase === 'uploading' && (
            <p role="status" className="mt-6 flex items-center justify-center gap-2 rounded-input bg-brand-soft p-5 font-semibold text-brand">
              <Loader2 className="animate-spin" size={20} /> Saving your private recording…
            </p>
          )}
          {phase === 'recorded' && (
            <div className="mt-6">
              {audioUrl && <audio className="w-full" controls src={audioUrl}>Your browser cannot play this recording.</audio>}
              {recording ? (
                <p className="mt-3 flex items-center gap-2 text-sm font-semibold text-good">
                  <CheckCircle2 size={17} /> Saved privately · {(recording.duration_ms / 1000).toFixed(1)} seconds
                </p>
              ) : (
                <Button variant="secondary" className="mt-3 w-full" onClick={() => void retryUpload()}>
                  <UploadCloud size={17} /> Retry private upload
                </Button>
              )}
              <div className="mt-5 grid gap-2 sm:grid-cols-2">
                <Button variant="secondary" disabled={!recording} onClick={() => void begin()}>
                  <RefreshCcw size={17} /> Replace draft
                </Button>
                <Button disabled={!recording || submitting} onClick={() => void submit()}>
                  <CheckCircle2 size={17} /> {submitting ? 'Submitting…' : 'Submit recording'}
                </Button>
              </div>
              <p className="mt-3 text-center text-xs text-muted">
                Replace draft records a fresh response over this unsent one. It does not start
                Attempt 2. Submission is final. Feedback is guided self-review, not an official score.
              </p>
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}

function preparationLabel(stimulus: SpeakingStimulus, remaining: number): string {
  if (!stimulus.prep_stages?.length) return 'Preparation time'
  let elapsed = stimulus.prep_seconds - remaining
  for (const stage of stimulus.prep_stages) {
    if (elapsed < stage.seconds) return stage.label
    elapsed -= stage.seconds
  }
  return stimulus.prep_stages.at(-1)?.label ?? 'Preparation time'
}

function Prompt({ stimulus }: { stimulus: SpeakingStimulus }) {
  return (
    <div>
      <p className="eyebrow">Your prompt</p>
      <h2 className="mt-2 text-2xl font-bold text-ink">{stimulus.prompt}</h2>
      <p className="mt-4 rounded-input border border-line bg-surface-secondary p-4 text-sm leading-7 text-ink">{stimulus.scenario}</p>
      {stimulus.image_url && (
        <img className="mt-5 aspect-[3/2] w-full rounded-card border border-line object-cover" src={stimulus.image_url} alt="Detailed original practice scene for this Speaking prompt" />
      )}
      {(stimulus.audience || stimulus.tone) && (
        <dl className="mt-4 grid gap-3 rounded-input border border-line p-4 text-sm sm:grid-cols-2">
          {stimulus.audience && <div><dt className="font-bold text-ink">Audience</dt><dd className="mt-1 text-muted">{stimulus.audience}</dd></div>}
          {stimulus.tone && <div><dt className="font-bold text-ink">Tone</dt><dd className="mt-1 text-muted">{stimulus.tone}</dd></div>}
        </dl>
      )}
      {stimulus.initial_options && (
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {stimulus.initial_options.map((option) => <OptionCard key={option.key} option={option} />)}
          {stimulus.competing_option && (
            <div className="sm:col-span-2"><p className="mb-2 text-xs font-bold uppercase text-accent">Other person's choice</p><OptionCard option={stimulus.competing_option} /></div>
          )}
        </div>
      )}
      {stimulus.choices && (
        <ul className="mt-5 grid gap-3 sm:grid-cols-2">{stimulus.choices.map((choice) => <li key={choice} className="rounded-input border border-line bg-surface p-4 text-sm font-semibold text-ink">{choice}</li>)}</ul>
      )}
      {stimulus.guidance && (
        <details className="mt-5 rounded-input border border-info/30 bg-info-bg p-4">
          <summary className="cursor-pointer text-sm font-bold text-ink">Planning guidance</summary>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink">{stimulus.guidance.map((tip) => <li key={tip}>{tip}</li>)}</ul>
        </details>
      )}
    </div>
  )
}

function OptionCard({ option }: { option: { key: string; label: string; details?: string[] } }) {
  return (
    <div className="rounded-input border border-line bg-surface p-4">
      <h3 className="font-bold text-ink">{option.label}</h3>
      {option.details && <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-muted">{option.details.map((detail) => <li key={detail}>{detail}</li>)}</ul>}
    </div>
  )
}

function Countdown({ label, seconds, recording }: { label: string; seconds: number; recording: boolean }) {
  return (
    <div className={`inline-flex items-center gap-2 rounded-full px-3 py-2 text-sm font-bold ${recording ? 'bg-bad-soft text-bad' : 'bg-brand-soft text-brand'}`}>
      {recording ? <Mic2 size={17} /> : <Clock3 size={17} />}
      <span>{label}: <span className="tabular-nums">{seconds}s</span></span>
    </div>
  )
}

function SpeakingReviewView({ session, review, recording, audioUrl, onBack }: { session: SpeakingSession; review: SpeakingReview; recording: SpeakingRecording; audioUrl: string; onBack: () => void }) {
  const attempt = session.attempt
  const isAttempt2 = attempt.attempt_number === 2
  const isMock = session.mode === 'mock'
  return (
    <div className="mx-auto max-w-4xl space-y-6 animate-fade-up">
      <Card className="overflow-hidden p-0 text-center">
        <div className="bg-brand px-5 py-8 text-white">
          <p className="text-xs font-bold uppercase tracking-widest text-accent-soft">{review.score_label}</p>
          <p className="mt-3 flex items-center justify-center gap-2 text-4xl font-bold"><CheckCircle2 size={30} /> Submitted</p>
          <p className="mt-2 text-lg font-semibold">{(recording.duration_ms / 1000).toFixed(1)} second recording</p>
          <p className="mt-3">
            <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-bold text-accent-soft">
              Attempt {attempt.attempt_number}
            </span>
          </p>
        </div>
        <p className="p-4 text-sm text-muted">{review.disclaimer}</p>
      </Card>

      {isAttempt2 && attempt.source_id && (
        <Card className="p-4">
          <p className="text-sm leading-6 text-ink">
            <strong>Attempt 1 is preserved.</strong> Your first response stays available for replay
            and comparison.
          </p>
          <ButtonLink to={`/speaking/session/${attempt.source_id}`} variant="secondary" className="mt-3">
            <ArrowLeft size={16} /> Open Attempt 1 review
          </ButtonLink>
        </Card>
      )}

      <Card className="p-5">
        <h2 className="text-xl font-bold text-ink">Replay your response</h2>
        {audioUrl ? <audio className="mt-3 w-full" controls src={audioUrl}>Your browser cannot play this recording.</audio> : <p className="mt-2 text-sm text-muted">Loading your private recording…</p>}
      </Card>
      <section aria-labelledby="speaking-review-title">
        <h2 id="speaking-review-title" className="text-2xl font-bold text-ink">Guided self-review</h2>
        <p className="mt-1 text-sm text-muted">{review.rubric.note}</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {review.rubric.dimensions.map((dimension) => (
            <Card key={dimension.key} className="p-5"><h3 className="font-bold text-ink">{dimension.label}</h3><p className="mt-2 text-sm leading-6 text-muted">{dimension.prompt}</p></Card>
          ))}
        </div>
      </section>
      <AIFeedbackPanel sessionId={session.id} />
      {!isMock && !isAttempt2 && <RetryAction sessionId={session.id} />}
      {!isMock && isAttempt2 && <SpeakingComparisonPanel sessionId={session.id} />}
      <Button onClick={onBack}>Choose another prompt</Button>
    </div>
  )
}

function SessionError({ message, onBack }: { message: string; onBack: () => void }) {
  return (
    <Card className="mx-auto max-w-xl text-center"><h1 className="text-2xl font-bold text-ink">Session unavailable</h1><p role="alert" className="mt-3 text-muted">{message}</p><Button className="mt-6" onClick={onBack}>Back to Speaking practice</Button></Card>
  )
}
