import { Bot, Loader2, Send, Trash2 } from 'lucide-react'
import { useEffect, useId, useRef } from 'react'
import { Button } from '../../components/ui'
import { STARTERS } from './coachData'
import { useAICoach } from './AICoachProvider'
import { CoachMarkdown } from './CoachMarkdown'

export function AICoachConversation({
  compact = false,
  autoFocus = false,
}: {
  compact?: boolean
  autoFocus?: boolean
}) {
  const {
    skill,
    draft,
    messages,
    loading,
    sending,
    error,
    setDraft,
    sendMessage,
  } = useAICoach()
  const logEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const questionId = useId()
  const fieldId = compact ? questionId : 'coach-page-question'

  useEffect(() => {
    if (typeof logEndRef.current?.scrollIntoView === 'function') {
      logEndRef.current.scrollIntoView({ block: 'end' })
    }
  }, [messages, sending])

  useEffect(() => {
    if (!autoFocus) return
    const timer = window.setTimeout(() => textareaRef.current?.focus(), 0)
    return () => window.clearTimeout(timer)
  }, [autoFocus])

  useEffect(() => {
    const field = textareaRef.current
    if (!field) return
    field.style.height = 'auto'
    field.style.height = `${field.scrollHeight}px`
  }, [draft])

  function chooseStarter(prompt: string) {
    setDraft(prompt)
    textareaRef.current?.focus()
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div
        role="log"
        aria-live="polite"
        aria-label="AI Coach conversation"
        className={compact ? 'scrollbar-none min-h-0 flex-1 space-y-4 overflow-x-hidden overflow-y-auto overscroll-contain px-3.5 py-4' : 'scrollbar-none min-h-0 flex-1 space-y-4 overflow-x-hidden overflow-y-auto overscroll-contain px-4 py-5 sm:px-5'}
      >
        {loading && messages.length === 0 && (
          <p role="status" className="flex items-center justify-center gap-2 py-16 text-sm text-muted">
            <Loader2 className="animate-spin text-brand" size={18} /> Loading conversation...
          </p>
        )}

        {!loading && messages.length === 0 && (
          <div className={compact ? 'py-5 text-center' : 'mx-auto max-w-xl py-8 text-center'}>
            <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-brand-soft text-brand">
              <Bot size={compact ? 21 : 24} />
            </span>
            <h3 className={`${compact ? 'mt-3 text-base' : 'mt-4 text-xl'} font-bold text-ink`}>
              What would you like to improve?
            </h3>
            <p className={`${compact ? 'mt-1.5 text-xs leading-5' : 'mt-2 text-sm leading-6'} text-muted`}>
              Ask a specific question, or choose a starting point below.
            </p>
            {compact && (
              <div className="mt-4 space-y-2 text-left">
                {STARTERS[skill].slice(0, 2).map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => chooseStarter(prompt)}
                    className="w-full rounded-xl bg-surface-secondary px-3 py-2.5 text-left text-xs leading-5 text-ink transition hover:bg-brand-soft hover:text-brand"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {messages.map((message) => (
          <article
            key={message.id}
            className={`min-w-0 ${message.role === 'user' ? 'ml-auto max-w-[85%]' : 'mr-auto max-w-full'}`}
          >
            <p className={`mb-1 text-[11px] font-bold uppercase tracking-wider ${message.role === 'user' ? 'text-right text-muted' : 'text-brand'}`}>
              {message.role === 'user' ? 'You' : 'AI Coach'}
            </p>
            <div
              className={`${compact ? 'rounded-xl px-3 py-2.5' : 'rounded-2xl px-4 py-3'} text-sm leading-6 ${
                message.role === 'user'
                  ? `${compact ? 'rounded-br-sm' : 'rounded-br-md'} bg-brand text-white shadow-sm`
                  : `${compact ? 'rounded-bl-sm' : 'rounded-bl-md'} bg-surface-secondary text-ink`
              }`}
            >
              {message.role === 'assistant'
                ? <CoachMarkdown content={message.content} />
                : <p className="whitespace-pre-wrap break-words">{message.content}</p>}
            </div>
          </article>
        ))}

        {sending && (
          <p role="status" className="flex items-center gap-2 text-sm text-muted">
            <Loader2 className="animate-spin text-brand" size={17} /> AI Coach is thinking...
          </p>
        )}
        <div ref={logEndRef} />
      </div>

      <form
        className={`bg-surface ${compact ? 'p-3' : 'p-3 sm:p-4'}`}
        onSubmit={(event) => {
          event.preventDefault()
          void sendMessage()
        }}
      >
        {error && (
          <p role="alert" className="mb-2 rounded-xl bg-bad-soft px-3 py-2 text-xs leading-5 text-bad sm:text-sm">
            {error}
          </p>
        )}
        <div className="flex items-end gap-2 rounded-2xl bg-surface-secondary p-1.5 pl-2 focus-within:ring-2 focus-within:ring-brand/25">
          <label htmlFor={fieldId} className="sr-only">Message the AI Coach</label>
          <textarea
            ref={textareaRef}
            id={fieldId}
            value={draft}
            maxLength={2000}
            rows={compact ? 1 : 2}
            placeholder="Ask about improving or answering a task..."
            className={`${compact ? 'min-h-10 max-h-28' : 'min-h-12 max-h-40'} scrollbar-none min-w-0 flex-1 resize-none bg-transparent px-2 py-2 text-sm leading-6 text-ink outline-none placeholder:text-muted`}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                void sendMessage()
              }
            }}
          />
          <Button
            type="submit"
            aria-label="Send question"
            disabled={sending || !draft.trim()}
            className={`${compact ? 'h-10 w-10' : 'h-11 w-11'} shrink-0 !p-0`}
          >
            {sending ? <Loader2 className="animate-spin" size={19} /> : <Send size={19} />}
          </Button>
        </div>
      </form>
    </div>
  )
}

export function AICoachClearDialog() {
  const { clearOpen, clearing, setClearOpen, clearConversation } = useAICoach()
  if (!clearOpen) return null

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-4">
      <div role="dialog" aria-modal="true" aria-labelledby="clear-coach-title" className="w-full max-w-md rounded-card bg-surface p-5 shadow-elevated">
        <Trash2 className="text-bad" size={22} />
        <h2 id="clear-coach-title" className="mt-3 text-xl font-bold text-ink">Clear this conversation?</h2>
        <p className="mt-2 text-sm leading-6 text-muted">This permanently removes all AI Coach messages from your account.</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={() => setClearOpen(false)}>Cancel</Button>
          <Button type="button" variant="danger" disabled={clearing} onClick={() => void clearConversation()}>
            {clearing ? <Loader2 className="animate-spin" size={17} /> : <Trash2 size={17} />} Clear chat
          </Button>
        </div>
      </div>
    </div>
  )
}
