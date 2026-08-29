import { useState } from 'react'
import { Download } from 'lucide-react'
import { Button, Card, CardTitle } from '../../components/ui'
import { ApiError, api } from '../../lib/api'

/** File-safe timestamp for the download filename (e.g. 2026-08-29T14-05-00). */
function timestampForFilename(now = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
  ].join('-') + 'T' + [pad(now.getHours()), pad(now.getMinutes()), pad(now.getSeconds())].join('-')
}

type ExportState = 'idle' | 'loading' | 'success' | 'error'

/**
 * Privacy-safe "Download my data". Fetches the export as a Blob and hands it
 * off through a temporary object URL so the browser saves a readable UTF-8
 * JSON file. Export contents are never read or logged by the client.
 */
export function DataExport() {
  const [state, setState] = useState<ExportState>('idle')
  const [error, setError] = useState<string | null>(null)

  async function onDownload() {
    setState('loading')
    setError(null)
    try {
      const blob = await api.getBlob('/me/export/')
      const url = URL.createObjectURL(blob)
      try {
        const link = document.createElement('a')
        link.href = url
        link.download = `celpip-data-export-${timestampForFilename()}.json`
        document.body.appendChild(link)
        link.click()
        link.remove()
      } finally {
        URL.revokeObjectURL(url)
      }
      setState('success')
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Could not prepare your data. Please try again.',
      )
      setState('error')
    }
  }

  return (
    <Card>
      <div className="mb-3 flex items-center gap-2.5">
        <Download size={20} className="shrink-0 text-accent" aria-hidden="true" />
        <CardTitle>Download my data</CardTitle>
      </div>
      <p className="mb-4 text-sm text-muted">
        Export a readable JSON copy of your profile, practice attempts,
        progress, mistakes, study plans, and mock results. Your password,
        recovery code, and private speaking recordings are never included.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="button"
          variant="secondary"
          onClick={onDownload}
          disabled={state === 'loading'}
        >
          {state === 'loading' ? 'Preparing…' : 'Download my data'}
        </Button>
        {state === 'success' && (
          <span role="status" className="text-sm text-good">
            Your download has started.
          </span>
        )}
        {state === 'error' && (
          <span role="alert" className="text-sm text-bad">
            {error}
          </span>
        )}
      </div>
    </Card>
  )
}
