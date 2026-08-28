import { useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { Button } from '../../components/ui'

/** One-time display of a recovery code with copy-to-clipboard and a confirm gate. */
export function RecoveryCodeNotice({
  code,
  onContinue,
}: {
  code: string
  onContinue: () => void
}) {
  const [copied, setCopied] = useState(false)
  const [acknowledged, setAcknowledged] = useState(false)

  async function copy() {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
    } catch {
      // Clipboard may be unavailable; the code is still visible to copy manually.
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-line bg-surface-secondary p-3">
        <p className="mb-1 text-xs font-semibold tracking-wide text-muted uppercase">
          Recovery code
        </p>
        <div className="flex items-center gap-2">
          <code className="flex-1 font-mono text-sm break-all text-ink" data-testid="recovery-code">
            {code}
          </code>
          <Button
            type="button"
            variant="secondary"
            onClick={copy}
            aria-label={copied ? 'Recovery code copied' : 'Copy recovery code'}
          >
            {copied ? <Check size={16} /> : <Copy size={16} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </Button>
        </div>
      </div>

      <label className="flex items-start gap-2 text-sm text-ink">
        <input
          type="checkbox"
          checked={acknowledged}
          onChange={(e) => setAcknowledged(e.target.checked)}
          className="mt-1 h-4 w-4"
        />
        <span>I have saved my recovery code somewhere safe.</span>
      </label>

      <Button
        type="button"
        onClick={onContinue}
        disabled={!acknowledged}
        className="w-full"
      >
        Continue
      </Button>
    </div>
  )
}
