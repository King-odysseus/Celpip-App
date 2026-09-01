import {
  AlertTriangle,
  CheckCircle2,
  Ear,
  Mic,
  MonitorCheck,
  RefreshCcw,
  ShieldAlert,
  Volume2,
} from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Button, Card, Meter } from '../../components/ui'

type SupportCheck = { id: string; label: string; ok: boolean }

function checkBrowserSupport(): SupportCheck[] {
  const hasAudioContext =
    typeof window !== 'undefined' &&
    (typeof AudioContext !== 'undefined' || typeof (window as unknown as { webkitAudioContext?: unknown }).webkitAudioContext !== 'undefined')
  return [
    { id: 'mic-api', label: 'Microphone access API', ok: typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia },
    { id: 'recorder', label: 'Audio recording (MediaRecorder)', ok: typeof MediaRecorder !== 'undefined' },
    { id: 'audio-playback', label: 'Audio playback', ok: typeof Audio !== 'undefined' },
    { id: 'audio-context', label: 'Audio output check', ok: hasAudioContext },
  ]
}

type MicState = 'idle' | 'requesting' | 'granted' | 'denied'

/** A short, real tone plus a live input meter — no fake pass/fail. */
function useSpeakerTest() {
  const [played, setPlayed] = useState(false)
  const [confirmed, setConfirmed] = useState<boolean | null>(null)
  const contextRef = useRef<AudioContext | null>(null)

  const play = useCallback(() => {
    const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    if (!Ctor) return
    const context = contextRef.current ?? new Ctor()
    contextRef.current = context
    const oscillator = context.createOscillator()
    const gain = context.createGain()
    oscillator.frequency.value = 440
    gain.gain.value = 0.15
    oscillator.connect(gain)
    gain.connect(context.destination)
    oscillator.start()
    oscillator.stop(context.currentTime + 0.9)
    setPlayed(true)
    setConfirmed(null)
  }, [])

  useEffect(() => () => void contextRef.current?.close(), [])

  return { played, confirmed, setConfirmed, play }
}

function useMicTest() {
  const [state, setState] = useState<MicState>('idle')
  const [level, setLevel] = useState(0)
  const streamRef = useRef<MediaStream | null>(null)
  const frameRef = useRef<number | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)

  const stop = useCallback(() => {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current)
    frameRef.current = null
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    void audioContextRef.current?.close()
    audioContextRef.current = null
    setLevel(0)
  }, [])

  const start = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setState('denied')
      return
    }
    setState('requesting')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      setState('granted')
      const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      const context = new Ctor()
      audioContextRef.current = context
      const analyser = context.createAnalyser()
      analyser.fftSize = 256
      context.createMediaStreamSource(stream).connect(analyser)
      const data = new Uint8Array(analyser.frequencyBinCount)
      const tick = () => {
        analyser.getByteFrequencyData(data)
        const average = data.reduce((sum, value) => sum + value, 0) / data.length
        setLevel(Math.min(100, Math.round((average / 128) * 100)))
        frameRef.current = requestAnimationFrame(tick)
      }
      tick()
    } catch {
      setState('denied')
    }
  }, [])

  useEffect(() => () => stop(), [stop])

  return { state, level, start, stop }
}

/**
 * Real device/audio checks plus an explicit rules acknowledgment, gating the
 * Start button on every mock attempt. Phase 12: browser support, speaker,
 * microphone, and the exam-mode rules a candidate needs before starting.
 */
export function MockPreflight({ onReady }: { onReady: () => void }) {
  const support = checkBrowserSupport()
  const allSupported = support.every((item) => item.ok)
  const speaker = useSpeakerTest()
  const mic = useMicTest()
  const [acknowledged, setAcknowledged] = useState(false)

  const speakerOk = speaker.confirmed === true
  const micOk = mic.state === 'granted'
  const allReady = allSupported && speakerOk && micOk && acknowledged

  return (
    <Card>
      <div className="flex items-center gap-2">
        <MonitorCheck size={20} className="text-accent" aria-hidden="true" />
        <h2 className="text-lg font-semibold tracking-tight text-ink">Before you start: device check</h2>
      </div>
      <p className="mt-1 text-sm text-muted">
        This mock uses one Listening playback, a hard section deadline, and holds all results
        until every component finishes. Confirm your device is ready before starting — you
        cannot pause the clock once a section begins.
      </p>

      <section aria-labelledby="preflight-support-title" className="mt-5">
        <h3 id="preflight-support-title" className="text-sm font-bold text-ink">Browser support</h3>
        <ul className="mt-2 space-y-1.5">
          {support.map((item) => (
            <li key={item.id} className="flex items-center gap-2 text-sm">
              {item.ok ? (
                <CheckCircle2 size={16} className="shrink-0 text-good" aria-hidden="true" />
              ) : (
                <AlertTriangle size={16} className="shrink-0 text-bad" aria-hidden="true" />
              )}
              <span className={item.ok ? 'text-ink' : 'text-bad'}>{item.label}</span>
            </li>
          ))}
        </ul>
        {!allSupported && (
          <p role="alert" className="mt-2 rounded-input bg-bad-soft p-3 text-sm text-bad">
            This browser is missing something this mock needs. Try a current Chrome, Edge,
            Firefox, or Safari release.
          </p>
        )}
      </section>

      <section aria-labelledby="preflight-speaker-title" className="mt-5 border-t border-line pt-5">
        <h3 id="preflight-speaker-title" className="flex items-center gap-2 text-sm font-bold text-ink">
          <Volume2 size={16} aria-hidden="true" /> Speaker check
        </h3>
        <p className="mt-1 text-sm text-muted">Play a short tone and confirm you heard it.</p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Button type="button" variant="secondary" onClick={speaker.play}>
            <Ear size={16} /> Play test tone
          </Button>
          {speaker.played && (
            <div className="flex items-center gap-2" role="group" aria-label="Did you hear the tone?">
              <Button
                type="button"
                variant={speakerOk ? 'primary' : 'secondary'}
                onClick={() => speaker.setConfirmed(true)}
              >
                I heard it
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => speaker.setConfirmed(false)}
              >
                I didn't hear it
              </Button>
            </div>
          )}
          {speakerOk && <CheckCircle2 size={18} className="text-good" aria-hidden="true" />}
        </div>
        {speaker.confirmed === false && (
          <p role="alert" className="mt-2 rounded-input bg-warn-bg p-3 text-sm text-ink">
            Check your system volume and output device, then play the tone again.
          </p>
        )}
      </section>

      <section aria-labelledby="preflight-mic-title" className="mt-5 border-t border-line pt-5">
        <h3 id="preflight-mic-title" className="flex items-center gap-2 text-sm font-bold text-ink">
          <Mic size={16} aria-hidden="true" /> Microphone check
        </h3>
        <p className="mt-1 text-sm text-muted">Needed for the Speaking section.</p>
        {mic.state === 'idle' && (
          <Button type="button" variant="secondary" className="mt-2" onClick={() => void mic.start()}>
            <Mic size={16} /> Test microphone
          </Button>
        )}
        {mic.state === 'requesting' && (
          <p role="status" className="mt-2 text-sm text-muted">Requesting microphone permission…</p>
        )}
        {mic.state === 'granted' && (
          <div className="mt-2 max-w-xs">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-good" aria-hidden="true" />
              <span className="text-sm text-ink">Microphone connected. Speak to see the level move.</span>
            </div>
            <div className="mt-2">
              <Meter value={mic.level} max={100} label="Microphone input level" />
            </div>
          </div>
        )}
        {mic.state === 'denied' && (
          <div className="mt-2 rounded-input bg-bad-soft p-3 text-sm text-bad">
            <p className="flex items-center gap-2 font-semibold">
              <ShieldAlert size={16} aria-hidden="true" /> Microphone permission was not granted.
            </p>
            <p className="mt-1">Allow microphone access in your browser's site settings, then try again.</p>
            <Button type="button" variant="secondary" className="mt-2" onClick={() => void mic.start()}>
              <RefreshCcw size={15} /> Try again
            </Button>
          </div>
        )}
      </section>

      <section className="mt-5 border-t border-line pt-5">
        <h3 className="text-sm font-bold text-ink">Exam-mode rules</h3>
        <ul className="mt-2 space-y-1.5 text-sm text-muted">
          <li>Each section has one server-controlled deadline; refreshing or losing connection never grants extra time.</li>
          <li>Every Listening recording plays only once in this timed mode.</li>
          <li>Corrections and results are held back until the entire mock is complete.</li>
          <li>Closing the tab is safe — reopen the same attempt from Mock Tests to resume exactly where the server left off.</li>
        </ul>
        <label className="mt-3 flex items-start gap-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(event) => setAcknowledged(event.target.checked)}
            className="mt-0.5 h-4 w-4 shrink-0"
          />
          <span>I understand these rules and I'm ready to begin.</span>
        </label>
      </section>

      <Button className="mt-5" disabled={!allReady} onClick={onReady}>
        Continue to start
      </Button>
    </Card>
  )
}
