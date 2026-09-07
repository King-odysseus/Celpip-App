import { Loader2, RotateCcw } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { ApiError, api } from '../../lib/api'
import type { WritingRetryResult } from './types'

function tokenHeaders(sessionId: string): Record<string, string> {
  const token = sessionStorage.getItem(`celpip-guest-${sessionId}`)
  return token ? { 'X-Guest-Token': token } : {}
}

export function WritingRetryAction({ sessionId }: { sessionId: string }) {
  const navigate = useNavigate()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')

  async function startRetry() {
    setPending(true)
    setError('')
    try {
      const result = await api.post<WritingRetryResult>(
        `/sessions/${sessionId}/writing/retry/`,
        undefined,
        tokenHeaders(sessionId),
      )
      const sourceToken = sessionStorage.getItem(`celpip-guest-${sessionId}`)
      if (sourceToken) sessionStorage.setItem(`celpip-guest-${result.id}`, sourceToken)
      navigate(result.launch_url)
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : 'A rewrite could not be started. Check your connection and try again.',
      )
      setPending(false)
    }
  }

  return (
    <Card className="border-dashed p-5">
      <h2 className="text-xl font-bold text-ink">Rewrite this response</h2>
      <p className="mt-2 text-sm leading-6 text-muted">
        Apply the feedback to the same prompt. Your first response remains saved so you can
        review both attempts.
      </p>
      {error && <p role="alert" className="mt-4 rounded-input bg-bad-soft p-3 text-sm text-bad">{error}</p>}
      <Button className="mt-5" onClick={() => void startRetry()} disabled={pending}>
        {pending ? <Loader2 className="animate-spin" size={17} /> : <RotateCcw size={17} />}
        {pending ? 'Starting…' : 'Rewrite this response'}
      </Button>
    </Card>
  )
}
