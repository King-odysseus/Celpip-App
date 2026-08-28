import { useState, type FormEvent } from 'react'
import { Button, Field } from '../../components/ui'
import { ApiError } from '../../lib/api'
import { FormError } from './AuthLayout'
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

function toNullableInt(value: string): number | null {
  return value === '' ? null : Number(value)
}

/** Editable learner profile — used for onboarding and ongoing edits on Account. */
export function ProfileForm({ profile }: { profile: LearnerProfile }) {
  const { updateProfile } = useAuth()
  const [form, setForm] = useState<LearnerProfile>(profile)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)

  function set<K extends keyof LearnerProfile>(key: K, value: LearnerProfile[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
    setSaved(false)
  }

  function toggleWeekday(iso: number) {
    const has = form.preferred_weekdays.includes(iso)
    const next = has
      ? form.preferred_weekdays.filter((d) => d !== iso)
      : [...form.preferred_weekdays, iso].sort((a, b) => a - b)
    set('preferred_weekdays', next)
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSaving(true)
    const changes: ProfileUpdate = {
      exam_date: form.exam_date || null,
      target_level: form.target_level,
      target_listening: form.target_listening,
      target_reading: form.target_reading,
      target_writing: form.target_writing,
      target_speaking: form.target_speaking,
      daily_minutes: form.daily_minutes,
      preferred_weekdays: form.preferred_weekdays,
      timezone: form.timezone,
    }
    try {
      await updateProfile(changes)
      setSaved(true)
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Could not save your profile.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <FormError message={error} />

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

      <Field
        label="Daily study minutes"
        name="daily_minutes"
        type="number"
        min={5}
        max={600}
        value={form.daily_minutes}
        onChange={(e) => set('daily_minutes', Number(e.target.value))}
      />

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

      <Field
        label="Timezone"
        name="timezone"
        value={form.timezone}
        onChange={(e) => set('timezone', e.target.value)}
        hint="IANA name, e.g. America/Toronto."
      />

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
