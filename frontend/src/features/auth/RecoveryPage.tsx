import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Field } from '../../components/ui'
import { ApiError, api } from '../../lib/api'
import { AuthLayout, FormError } from './AuthLayout'
import { RecoveryCodeNotice } from './RecoveryCodeNotice'

const MIN_PASSWORD = 6

type ResetResponse = { recovery_code: string }

export function RecoveryPage() {
  const navigate = useNavigate()
  const [identifier, setIdentifier] = useState('')
  const [recoveryCode, setRecoveryCode] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [newCode, setNewCode] = useState<string | null>(null)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (newPassword.length < MIN_PASSWORD) {
      setError(`Password must be at least ${MIN_PASSWORD} characters.`)
      return
    }
    setSubmitting(true)
    try {
      const data = await api.post<ResetResponse>('/auth/recovery-code/reset/', {
        identifier: identifier.trim(),
        recovery_code: recoveryCode.trim(),
        new_password: newPassword,
      })
      setNewCode(data.recovery_code)
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Something went wrong. Please try again.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  if (newCode) {
    return (
      <AuthLayout
        eyebrow="Password reset"
        title="Save your new recovery code"
        description="Your old code has been used. Here is a fresh one — store it safely, then sign in with your new password."
      >
        <RecoveryCodeNotice
          code={newCode}
          onContinue={() => navigate('/signin', { replace: true })}
        />
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      eyebrow="Account recovery"
      title="Reset with a recovery code"
      description="Enter your identifier, the one-time recovery code you saved, and a new password."
      footer={
        <>
          Remembered it?{' '}
          <Link to="/signin" className="font-semibold text-brand hover:underline">
            Back to sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <FormError message={error} />
        <Field
          label="Username or email"
          name="identifier"
          autoComplete="username"
          required
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
        />
        <Field
          label="Recovery code"
          name="recovery_code"
          required
          value={recoveryCode}
          onChange={(e) => setRecoveryCode(e.target.value)}
        />
        <Field
          label="New password"
          name="new_password"
          type="password"
          autoComplete="new-password"
          required
          minLength={MIN_PASSWORD}
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          hint={`At least ${MIN_PASSWORD} characters.`}
        />
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? 'Resetting…' : 'Reset password'}
        </Button>
      </form>
    </AuthLayout>
  )
}
