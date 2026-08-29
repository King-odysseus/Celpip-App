import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2 } from 'lucide-react'
import { Button, Card, CardTitle, Field } from '../../components/ui'
import { ApiError, api } from '../../lib/api'
import { useAuth } from './AuthProvider'

type ConfirmationMethod = 'password' | 'recovery_code'

const PANEL_ID = 'delete-account-panel'

/**
 * Self-service account deletion. Deliberately a multi-step danger zone: an
 * explicit first action reveals the confirmation panel, which requires either
 * the account password or the unused recovery code — never both.
 */
export function DeleteAccount() {
  const { clearSession } = useAuth()
  const navigate = useNavigate()

  const [open, setOpen] = useState(false)
  const [method, setMethod] = useState<ConfirmationMethod>('password')
  const [password, setPassword] = useState('')
  const [recoveryCode, setRecoveryCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  const triggerRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const shouldRefocus = useRef(false)

  function openPanel() {
    setOpen(true)
    setError(null)
    setPassword('')
    setRecoveryCode('')
  }

  const closePanel = useCallback(() => {
    // Once deletion is in flight the panel must stay mounted so the user sees
    // the pending state through to completion; refuse any dismissal attempt.
    if (deleting) return
    shouldRefocus.current = true
    setOpen(false)
    setError(null)
    // Drop any credentials immediately so stale secrets never linger in state
    // while the panel is closed.
    setPassword('')
    setRecoveryCode('')
  }, [deleting])

  // Move focus into the newly revealed panel and keep Escape a safe way out.
  useEffect(() => {
    if (!open) return
    panelRef.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        closePanel()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, closePanel])

  // Return focus to the trigger once it remounts after the panel closes.
  useEffect(() => {
    if (open || !shouldRefocus.current) return
    shouldRefocus.current = false
    triggerRef.current?.focus()
  }, [open])

  async function onConfirm(event: FormEvent) {
    event.preventDefault()
    setError(null)

    const body =
      method === 'password'
        ? { password }
        : { recovery_code: recoveryCode.trim() }

    if (!body.password && !body.recovery_code) {
      setError(
        method === 'password'
          ? 'Enter your password to delete the account.'
          : 'Enter your recovery code to delete the account.',
      )
      return
    }

    setDeleting(true)
    try {
      await api.del('/me/', body)
      // Commit the navigation synchronously before dropping the session, so
      // the ProtectedRoute never sees an anonymous visitor still on /account
      // (react-router wraps navigations in startTransition by default).
      navigate('/', {
        replace: true,
        state: { notice: 'Your account has been deleted.' },
        flushSync: true,
      })
      clearSession()
      // The page is navigating away; do not reset local state after unmount.
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Something went wrong. Please try again.',
      )
      setDeleting(false)
    }
  }

  return (
    <Card className="border-bad/40 bg-bad-soft/20">
      <div className="mb-3 flex items-center gap-2.5">
        <Trash2 size={20} className="shrink-0 text-bad" aria-hidden="true" />
        <CardTitle>Danger zone</CardTitle>
      </div>

      {!open ? (
        <div className="space-y-4">
          <p className="text-sm text-muted">
            Permanently delete your account and all associated data.
          </p>
          <Button
            ref={triggerRef}
            type="button"
            variant="danger"
            onClick={openPanel}
            aria-expanded={open}
            aria-controls={PANEL_ID}
          >
            Delete account
          </Button>
        </div>
      ) : (
        <div
          id={PANEL_ID}
          ref={panelRef}
          tabIndex={-1}
          role="region"
          aria-labelledby="delete-account-confirm-title"
          className="rounded-xl border border-bad/30 bg-surface p-4 outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
        >
          <h3
            id="delete-account-confirm-title"
            className="mb-2 text-base font-semibold tracking-tight text-ink"
          >
            Delete your account?
          </h3>
          <p className="mb-4 rounded-xl border border-bad/40 bg-bad-soft px-3 py-2 text-sm text-bad">
            This is permanent and cannot be undone. Your profile, exam dates,
            targets, progress, practice attempts, mistakes, study plans, mock
            results, and private speaking recordings will all be deleted.
          </p>

          <form onSubmit={onConfirm} className="space-y-4" noValidate>
            {error && (
              <p
                role="alert"
                className="rounded-xl border border-bad/40 bg-bad-soft px-3 py-2 text-sm text-bad"
              >
                {error}
              </p>
            )}

            <fieldset>
              <legend className="mb-1.5 text-sm font-medium text-ink">
                Confirm with
              </legend>
              <div className="flex flex-wrap gap-x-5 gap-y-2">
                <label className="flex items-center gap-2 text-sm text-ink">
                  <input
                    type="radio"
                    name="confirmation-method"
                    value="password"
                    checked={method === 'password'}
                    onChange={() => {
                      setMethod('password')
                      // Clear the other method's credential so a stale secret
                      // cannot be submitted later or resurface on switching.
                      setRecoveryCode('')
                      setError(null)
                    }}
                    className="h-4 w-4"
                  />
                  Password
                </label>
                <label className="flex items-center gap-2 text-sm text-ink">
                  <input
                    type="radio"
                    name="confirmation-method"
                    value="recovery_code"
                    checked={method === 'recovery_code'}
                    onChange={() => {
                      setMethod('recovery_code')
                      // Clear the other method's credential so a stale secret
                      // cannot be submitted later or resurface on switching.
                      setPassword('')
                      setError(null)
                    }}
                    className="h-4 w-4"
                  />
                  Recovery code
                </label>
              </div>
            </fieldset>

            {method === 'password' ? (
              <Field
                label="Your password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            ) : (
              <Field
                label="Your recovery code"
                name="recovery_code"
                required
                value={recoveryCode}
                onChange={(e) => setRecoveryCode(e.target.value)}
              />
            )}

            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="submit"
                variant="danger"
                disabled={deleting}
              >
                {deleting ? 'Deleting…' : 'Permanently delete account'}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={closePanel}
                disabled={deleting}
              >
                Cancel
              </Button>
            </div>
          </form>
        </div>
      )}
    </Card>
  )
}
