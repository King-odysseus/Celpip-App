import { Loader2, RotateCcw } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { ApiError } from '../../lib/api'
import { createSpeakingRetry } from './api'
import { tokenHeaders } from './token'

/**
 * Prominent action on a submitted non-mock Attempt 1 review that starts the one
 * Attempt 2. It copies the source session's guest token to the retry session so
 * a loose (unauthenticated) learner stays authorized after navigation.
 */
export function RetryAction({ sessionId }: { sessionId: string }) {
  const navigate = useNavigate()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')

  async function retry() {
    setPending(true)
    setError('')
    try {
      const result = await createSpeakingRetry(sessionId, tokenHeaders(sessionId))
      const sourceToken = sessionStorage.getItem(`celpip-guest-${sessionId}`)
      if (sourceToken) {
        sessionStorage.setItem(`celpip-guest-${result.id}`, sourceToken)
      }
      navigate(result.launch_url)
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : 'A second attempt could not be started. Check your connection and try again.',
      )
      setPending(false)
    }
  }

  return (
    <Card className="border-dashed p-5">
      <h2 className="text-xl font-bold text-ink">Try this task again</h2>
      <p className="mt-2 text-sm leading-6 text-muted">
        Keep this response and record a second attempt. Attempt 1 stays available so you can
        compare the two.
      </p>
      {error && (
        <p role="alert" className="mt-4 rounded-input bg-bad-soft p-3 text-sm text-bad">
          {error}
        </p>
      )}
      <Button className="mt-5" onClick={() => void retry()} disabled={pending}>
        {pending ? <Loader2 className="animate-spin" size={17} /> : <RotateCcw size={17} />}
        {pending ? 'Starting…' : 'Try this task again'}
      </Button>
    </Card>
  )
}
