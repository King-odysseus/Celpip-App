import { Flag } from 'lucide-react'
import { useState } from 'react'
import { Button } from '../../components/ui'
import { api } from '../../lib/api'

type IssueType = 'audio_mismatch' | 'missing_text' | 'ambiguous_answer' | 'other'

export function ReportContentIssue({ sessionId, hasAudio = false }: { sessionId: string; hasAudio?: boolean }) {
  const [open, setOpen] = useState(false)
  const [issueType, setIssueType] = useState<IssueType>(hasAudio ? 'audio_mismatch' : 'ambiguous_answer')
  const [detail, setDetail] = useState('')
  const [state, setState] = useState<'idle' | 'sending' | 'sent'>('idle')
  const [error, setError] = useState('')

  async function submit() {
    setState('sending')
    const guestToken = sessionStorage.getItem(`celpip-guest-${sessionId}`)
    try {
      await api.post(`/sessions/${sessionId}/content-issue/`, { issue_type: issueType, detail }, guestToken ? { 'X-Guest-Token': guestToken } : undefined)
      setState('sent')
    } catch {
      setState('idle')
      setError('The report could not be sent. Please try again.')
    }
  }

  if (state === 'sent') return <p className="text-sm font-semibold text-good">Thanks. This content has been sent for review.</p>
  return (
    <div className="rounded-input border border-line bg-surface p-4">
      <button type="button" onClick={() => setOpen((value) => !value)} className="flex items-center gap-2 text-sm font-semibold text-muted hover:text-ink">
        <Flag size={16} /> Report a problem with this question set
      </button>
      {open && (
        <div className="mt-3 space-y-3">
          <select value={issueType} onChange={(event) => setIssueType(event.target.value as IssueType)} className="w-full rounded-input border border-line bg-surface px-3 py-2 text-sm">
            {hasAudio && <option value="audio_mismatch">Audio does not match</option>}
            <option value="missing_text">Text is incomplete</option>
            <option value="ambiguous_answer">An answer is ambiguous or unsupported</option>
            <option value="other">Another problem</option>
          </select>
          <textarea value={detail} onChange={(event) => setDetail(event.target.value)} maxLength={1000} rows={3} placeholder="Tell us what did not match or which question was affected." className="w-full rounded-input border border-line bg-surface px-3 py-2 text-sm" />
          <Button variant="secondary" disabled={state === 'sending'} onClick={() => void submit()}>{state === 'sending' ? 'Sending…' : 'Send report'}</Button>
          {error && <p role="alert" className="text-sm text-bad">{error}</p>}
        </div>
      )}
    </div>
  )
}
