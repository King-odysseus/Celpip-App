import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Field } from '../../components/ui'
import { ApiError } from '../../lib/api'
import { AuthLayout, FormError } from './AuthLayout'
import { useAuth } from './AuthProvider'
import { RecoveryCodeNotice } from './RecoveryCodeNotice'

const MIN_PASSWORD = 6

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [recoveryCode, setRecoveryCode] = useState<string | null>(null)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (password.length < MIN_PASSWORD) {
      setError(`Password must be at least ${MIN_PASSWORD} characters.`)
      return
    }
    setSubmitting(true)
    try {
      const { recoveryCode: code } = await register(identifier.trim(), password)
      setRecoveryCode(code)
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

  if (recoveryCode) {
    return (
      <AuthLayout
        eyebrow="Account created"
        title="Save your recovery code"
        description="This is the only time it will be shown. Store it somewhere safe — it can reset your password if you are locked out."
      >
        <RecoveryCodeNotice
          code={recoveryCode}
          onContinue={() => navigate('/account', { replace: true })}
        />
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      eyebrow="Get started"
      title="Create your account"
      description="Just one identifier and a password. No email confirmation required to start practising."
      footer={
        <>
          Already have an account?{' '}
          <Link to="/signin" className="font-semibold text-brand hover:underline">
            Sign in
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
          hint="Case-insensitive. You can use a username or an email address."
        />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={MIN_PASSWORD}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          hint={`At least ${MIN_PASSWORD} characters.`}
        />
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? 'Creating account…' : 'Create account'}
        </Button>
      </form>
    </AuthLayout>
  )
}
