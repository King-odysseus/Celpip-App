import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { ApiError } from '../../lib/api'
import { advanceMock } from './api'

/**
 * Neutral state shown when a mock task's session is already submitted but its
 * corrections remain embargoed until the full four-component mock finishes.
 *
 * It advances the parent mock before returning to the workspace so a child that
 * submitted but whose advance previously failed/crashed can't loop forever when
 * reopened: the server treats a repeated advance as an idempotent replay, so a
 * stale-order retry resolves to success and the workspace reconciles state.
 */
export function MockReturnNotice({
  attemptId,
  taskOrder,
  returnUrl,
  title = 'Task submitted',
  message = 'Corrections are released after all four mock components finish.',
}: {
  attemptId: string
  taskOrder: number
  returnUrl: string
  title?: string
  message?: string
}) {
  const navigate = useNavigate()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')

  async function continueToMock() {
    setPending(true)
    setError('')
    try {
      await advanceMock(attemptId, taskOrder)
      navigate(returnUrl)
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : 'The mock could not be advanced. Check your connection and try again.',
      )
      setPending(false)
    }
  }

  return (
    <Card className="mx-auto max-w-xl text-center">
      <h1 className="text-2xl font-bold text-ink">{title}</h1>
      <p className="mt-3 text-muted">{message}</p>
      {pending && (
        <p role="status" className="mt-4 text-sm font-semibold text-muted">
          Returning to your mock…
        </p>
      )}
      {error && (
        <p role="alert" className="mt-4 rounded-input bg-bad-soft p-3 text-sm text-bad">
          {error}
        </p>
      )}
      <Button
        className="mt-6"
        onClick={() => void continueToMock()}
        disabled={pending}
      >
        {pending ? 'Returning…' : error ? 'Retry' : 'Return to mock'}
      </Button>
    </Card>
  )
}
