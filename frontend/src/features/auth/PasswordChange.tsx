import { useState, type FormEvent } from 'react'
import { Button, Card, CardTitle } from '../../components/ui'
import { ApiError } from '../../lib/api'
import { useAuth } from './AuthProvider'

const MIN_PASSWORD_LENGTH = 6

export function PasswordChange() {
  const { changePassword } = useAuth()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [saving, setSaving] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSuccess('')
    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      setError(`New password must be at least ${MIN_PASSWORD_LENGTH} characters.`)
      return
    }
    if (newPassword !== confirmation) {
      setError('New passwords do not match.')
      return
    }
    setSaving(true)
    try {
      await changePassword(currentPassword, newPassword)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmation('')
      setSuccess('Password updated. Other signed-in sessions have been revoked.')
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Could not update your password.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardTitle>Change password</CardTitle>
      <p className="mt-1 text-sm text-muted">Use your current password to choose a new one.</p>
      <form className="mt-4 space-y-4" onSubmit={submit}>
        <label className="block text-sm font-medium text-ink">
          Current password
          <input className="mt-1 min-h-11 w-full rounded-input border border-line bg-surface px-3" type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required />
        </label>
        <label className="block text-sm font-medium text-ink">
          New password
          <input className="mt-1 min-h-11 w-full rounded-input border border-line bg-surface px-3" type="password" autoComplete="new-password" minLength={MIN_PASSWORD_LENGTH} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required />
        </label>
        <label className="block text-sm font-medium text-ink">
          Confirm new password
          <input className="mt-1 min-h-11 w-full rounded-input border border-line bg-surface px-3" type="password" autoComplete="new-password" minLength={MIN_PASSWORD_LENGTH} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required />
        </label>
        {error && <p role="alert" className="rounded-input bg-bad-soft p-3 text-sm text-bad">{error}</p>}
        {success && <p role="status" className="rounded-input bg-good-soft p-3 text-sm text-good">{success}</p>}
        <Button type="submit" disabled={saving}>{saving ? 'Updating…' : 'Update password'}</Button>
      </form>
    </Card>
  )
}
