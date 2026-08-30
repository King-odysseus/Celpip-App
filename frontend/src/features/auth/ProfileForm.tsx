import { useRef, useState, type FormEvent } from 'react'
import { Button, Field } from '../../components/ui'
import { ApiError } from '../../lib/api'
import { useAuth } from './AuthProvider'
import { SKILLS, type LearnerProfile, type ProfileUpdate } from './types'

const WEEKDAYS: Array<{ iso: number; label: string; short: string }> = [
  { iso: 1, label: 'Monday', short: 'Mon' },
  { iso: 2, label: 'Tuesday', short: 'Tue' },
  { iso: 3, label: 'Wednesday', short: 'Wed' },
  { iso: 4, label: 'Thursday', short: 'Thu' },
  { iso: 5, label: 'Friday', short: 'Fri' },
  { iso: 6, label: 'Saturday', short: 'Sat' },
  { iso: 7, label: 'Sunday', short: 'Sun' },
]

const LEVELS = Array.from({ length: 12 }, (_, i) => i + 1)

/** A short, curated set of IANA zones covering Canadian test-takers plus UTC/UK. */
const BASE_TIMEZONES = [
  'UTC',
  'America/St_Johns',
  'America/Halifax',
  'America/Toronto',
  'America/Winnipeg',
  'America/Edmonton',
  'America/Vancouver',
  'Europe/London',
]

/** Human labels for the profile fields the backend can reject. */
const FIELD_LABELS: Record<string, string> = {
  timezone: 'Timezone',
  daily_minutes: 'Daily minutes',
  exam_date: 'Exam date',
  target_level: 'Target level',
  target_listening: 'Listening target',
  target_reading: 'Reading target',
  target_writing: 'Writing target',
  target_speaking: 'Speaking target',
  preferred_weekdays: 'Preferred study days',
}

/** Controls we can move focus to when the matching field is invalid. */
const FOCUSABLE_FIELDS = ['daily_minutes', 'timezone'] as const

function labelFor(key: string): string {
  return (
    FIELD_LABELS[key] ??
    key.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())
  )
}

/**
 * Render a single field's error value as plain text. The backend (DRF) may send
 * a string, an array of strings, or a nested object of the same — this flattens
 * any of those without ever emitting `[object Object]` or raw JSON.
 */
function flattenValue(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) {
    return value.map(flattenValue).filter(Boolean).join(' ')
  }
  if (typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, inner]) => {
        const text = flattenValue(inner)
        return text ? `${labelFor(key)}: ${text}` : ''
      })
      .filter(Boolean)
      .join(' ')
  }
  return ''
}

/** Turn an ApiError.fields map into readable, field-labelled bullet strings. */
export function formatFieldErrors(fields: Record<string, unknown>): string[] {
  return Object.entries(fields)
    .map(([key, value]) => {
      const text = flattenValue(value)
      return text ? `${labelFor(key)}: ${text}` : ''
    })
    .filter(Boolean)
}

/** First rejected field we can move focus to, in a sensible priority order. */
function firstFocusableInvalid(fields: Record<string, unknown>): string | null {
  return FOCUSABLE_FIELDS.find((key) => key in fields) ?? null
}

function toNullableInt(value: string): number | null {
  return value === '' ? null : Number(value)
}

/** True when `tz` is a non-empty IANA zone the browser recognises. */
function isValidTimeZone(tz: string): boolean {
  if (!tz.trim()) return false
  try {
    new Intl.DateTimeFormat(undefined, { timeZone: tz })
    return true
  } catch {
    return false
  }
}

/** Editable learner profile — used for onboarding and ongoing edits on Account. */
export function ProfileForm({ profile }: { profile: LearnerProfile }) {
  const { updateProfile } = useAuth()
  const [form, setForm] = useState<LearnerProfile>(profile)
  // Daily minutes is edited as a string so an in-progress empty field never
  // collapses to Number('') === 0.
  const [minutesInput, setMinutesInput] = useState<string>(
    String(profile.daily_minutes),
  )
  const [tzOptions, setTzOptions] = useState<string[]>(() =>
    profile.timezone && !BASE_TIMEZONES.includes(profile.timezone)
      ? [...BASE_TIMEZONES, profile.timezone]
      : BASE_TIMEZONES,
  )
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<string[]>([])
  const [invalidField, setInvalidField] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)

  const minutesRef = useRef<HTMLInputElement>(null)
  const timezoneRef = useRef<HTMLSelectElement>(null)

  function set<K extends keyof LearnerProfile>(key: K, value: LearnerProfile[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
    setSaved(false)
  }

  function focusField(name: string) {
    if (name === 'daily_minutes') minutesRef.current?.focus()
    else if (name === 'timezone') timezoneRef.current?.focus()
  }

  function clearErrors() {
    setError(null)
    setFieldErrors([])
    setInvalidField(null)
  }

  function toggleWeekday(iso: number) {
    const has = form.preferred_weekdays.includes(iso)
    const next = has
      ? form.preferred_weekdays.filter((d) => d !== iso)
      : [...form.preferred_weekdays, iso].sort((a, b) => a - b)
    set('preferred_weekdays', next)
  }

  function useBrowserTimezone() {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
    if (!isValidTimeZone(tz)) {
      setError(
        'Your browser did not report a valid timezone. Please choose one from the list.',
      )
      setFieldErrors([])
      setInvalidField('timezone')
      focusField('timezone')
      return
    }
    setTzOptions((prev) => (prev.includes(tz) ? prev : [...prev, tz]))
    set('timezone', tz)
    if (invalidField === 'timezone') clearErrors()
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    clearErrors()

    // ── Client validation — block the PATCH on invalid local input ──────────
    const trimmedMinutes = minutesInput.trim()
    const minutes = Number(trimmedMinutes)
    if (!/^\d+$/.test(trimmedMinutes) || minutes < 5 || minutes > 600) {
      setError(
        'Enter your daily study minutes as a whole number between 5 and 600.',
      )
      setInvalidField('daily_minutes')
      focusField('daily_minutes')
      return
    }

    if (!isValidTimeZone(form.timezone)) {
      setError('Choose a valid timezone before saving.')
      setFieldErrors([
        'Timezone: Use a valid IANA timezone such as Europe/London.',
      ])
      setInvalidField('timezone')
      focusField('timezone')
      return
    }

    setSaving(true)
    const changes: ProfileUpdate = {
      exam_date: form.exam_date || null,
      target_level: form.target_level,
      target_listening: form.target_listening,
      target_reading: form.target_reading,
      target_writing: form.target_writing,
      target_speaking: form.target_speaking,
      daily_minutes: minutes,
      preferred_weekdays: form.preferred_weekdays,
      timezone: form.timezone,
    }
    try {
      await updateProfile(changes)
      setSaved(true)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || 'Some fields were invalid.')
        setFieldErrors(formatFieldErrors(err.fields))
        const focus = firstFocusableInvalid(err.fields)
        if (focus) {
          setInvalidField(focus)
          focusField(focus)
        }
      } else {
        setError('Could not save your profile.')
      }
    } finally {
      setSaving(false)
    }
  }

  const showAlert = Boolean(error) || fieldErrors.length > 0
  const minutesInvalid = invalidField === 'daily_minutes'
  const timezoneInvalid = invalidField === 'timezone'

  return (
    <form onSubmit={onSubmit} className="space-y-6" noValidate>
      {showAlert && (
        <div
          id="profile-errors"
          role="alert"
          className="space-y-1 rounded-xl border border-bad/40 bg-bad-soft px-3 py-2 text-sm text-bad"
        >
          {error && <p>{error}</p>}
          {fieldErrors.length > 0 && (
            <ul className="list-disc space-y-0.5 pl-5">
              {fieldErrors.map((message) => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      <Field
        label="Exam date"
        name="exam_date"
        type="date"
        value={form.exam_date ?? ''}
        onChange={(e) => set('exam_date', e.target.value || null)}
        hint="Used for your dashboard countdown."
      />

      <div>
        <label
          htmlFor="target_level"
          className="mb-1.5 block text-sm font-medium text-ink"
        >
          Default target level
        </label>
        <select
          id="target_level"
          value={form.target_level}
          onChange={(e) => set('target_level', Number(e.target.value))}
          className="min-h-11 w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-ink focus-visible:border-brand focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand"
        >
          {LEVELS.map((level) => (
            <option key={level} value={level}>
              CELPIP {level}
            </option>
          ))}
        </select>
        <span className="mt-1.5 block text-xs text-muted">
          Applies to every skill unless you set an override below.
        </span>
      </div>

      <fieldset className="space-y-3">
        <legend className="text-sm font-medium text-ink">
          Per-skill targets (optional)
        </legend>
        <div className="grid grid-cols-2 gap-3">
          {SKILLS.map((skill) => {
            const key = `target_${skill}` as const
            const inputId = `target-${skill}`
            return (
              <div key={skill}>
                <label
                  htmlFor={inputId}
                  className="mb-1.5 block text-sm text-ink capitalize"
                >
                  {skill}
                </label>
                <select
                  id={inputId}
                  value={form[key] ?? ''}
                  onChange={(e) => set(key, toNullableInt(e.target.value))}
                  className="min-h-11 w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-ink focus-visible:border-brand focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand"
                >
                  <option value="">Use default</option>
                  {LEVELS.map((level) => (
                    <option key={level} value={level}>
                      CELPIP {level}
                    </option>
                  ))}
                </select>
              </div>
            )
          })}
        </div>
      </fieldset>

      <div className="block">
        <label
          htmlFor="daily_minutes"
          className="mb-1.5 block text-sm font-medium text-ink"
        >
          Daily study minutes
        </label>
        <input
          ref={minutesRef}
          id="daily_minutes"
          name="daily_minutes"
          type="number"
          inputMode="numeric"
          min={5}
          max={600}
          value={minutesInput}
          onChange={(e) => {
            setMinutesInput(e.target.value)
            setSaved(false)
          }}
          aria-invalid={minutesInvalid || undefined}
          aria-describedby={
            minutesInvalid
              ? 'profile-errors daily_minutes-hint'
              : 'daily_minutes-hint'
          }
          className="min-h-11 w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-ink focus-visible:border-brand focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand"
        />
        <span id="daily_minutes-hint" className="mt-1.5 block text-xs text-muted">
          A whole number between 5 and 600 minutes.
        </span>
      </div>

      <fieldset>
        <legend className="mb-1.5 text-sm font-medium text-ink">
          Preferred study days
        </legend>
        <div className="flex flex-wrap gap-2">
          {WEEKDAYS.map((day) => {
            const active = form.preferred_weekdays.includes(day.iso)
            return (
              <button
                key={day.iso}
                type="button"
                aria-pressed={active}
                aria-label={day.label}
                onClick={() => toggleWeekday(day.iso)}
                className={`min-h-11 min-w-11 rounded-full border px-3 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${
                  active
                    ? 'border-brand bg-brand-soft text-brand'
                    : 'border-line text-muted hover:text-ink'
                }`}
              >
                {day.short}
              </button>
            )
          })}
        </div>
      </fieldset>

      <div className="block">
        <label
          htmlFor="timezone"
          className="mb-1.5 block text-sm font-medium text-ink"
        >
          Timezone
        </label>
        <div className="flex flex-wrap items-center gap-2">
          <select
            ref={timezoneRef}
            id="timezone"
            name="timezone"
            value={form.timezone}
            onChange={(e) => set('timezone', e.target.value)}
            aria-invalid={timezoneInvalid || undefined}
            aria-describedby={
              timezoneInvalid ? 'profile-errors timezone-hint' : 'timezone-hint'
            }
            className="min-h-11 flex-1 rounded-xl border border-line bg-surface px-3 py-2.5 text-ink focus-visible:border-brand focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand"
          >
            {tzOptions.map((tz) => (
              <option key={tz} value={tz}>
                {tz}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={useBrowserTimezone}
            className="min-h-11 rounded-xl border border-line px-3 text-sm font-medium text-ink transition-colors hover:border-brand hover:text-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            Use my timezone
          </button>
        </div>
        <span id="timezone-hint" className="mt-1.5 block text-xs text-muted">
          IANA name, e.g. America/Toronto.
        </span>
      </div>

      <div className="flex items-center gap-3">
        <Button type="submit" disabled={saving}>
          {saving ? 'Saving…' : 'Save profile'}
        </Button>
        {saved && (
          <span role="status" className="text-sm text-good">
            Profile saved.
          </span>
        )}
      </div>
    </form>
  )
}
