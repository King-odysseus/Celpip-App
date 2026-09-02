import { CheckCircle2 } from 'lucide-react'
import { useState } from 'react'
import { Button, ButtonLink } from '../../components/ui'
import { api } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'

export function StudyTaskAction({ taskId }: { taskId: string | null }) {
  const { status } = useAuth()
  const [completed, setCompleted] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  if (status !== 'authenticated' || !taskId) return null

  async function markComplete() {
    setSaving(true)
    setError('')
    try {
      await api.patch(`/me/study-plan/tasks/${taskId}/`, { state: 'completed' })
      setCompleted(true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not mark the study task complete.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-input border border-brand/30 bg-brand-soft p-4">
      {completed ? (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="flex items-center gap-2 text-sm font-semibold text-good">
            <CheckCircle2 size={18} /> Study Plan task completed
          </p>
          <ButtonLink to="/study-plan" variant="secondary">
            Return to Study Plan
          </ButtonLink>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm font-semibold text-ink">This lesson is in your Study Plan.</p>
            <Button variant="secondary" disabled={saving} onClick={() => setConfirming(true)}>
              Mark as complete
            </Button>
          </div>
          {confirming && (
            <div className="mt-3 rounded-input border border-brand/30 bg-surface p-3" role="dialog" aria-label="Confirm lesson understanding">
              <p className="text-sm font-semibold text-ink">Do you understand this lesson?</p>
              <p className="mt-1 text-xs text-muted">Confirm only after completing the recommended practice.</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button disabled={saving} onClick={() => void markComplete()}>
                  {saving ? 'Saving…' : 'Yes, I understand'}
                </Button>
                <Button variant="ghost" disabled={saving} onClick={() => setConfirming(false)}>Not yet</Button>
              </div>
            </div>
          )}
        </>
      )}
      {error && <p role="alert" className="mt-2 text-xs text-bad">{error}</p>}
    </div>
  )
}
