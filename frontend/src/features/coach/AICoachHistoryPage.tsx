import { History, Loader2, MessageSquare, Plus, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { useAICoach } from './AICoachProvider'
import { COACH_SKILLS, type CoachConversation } from './coachData'

type PendingDelete = { kind: 'one'; conversation: CoachConversation } | { kind: 'all' }

function formatUpdated(value: string) {
  const date = new Date(value)
  const sameYear = date.getFullYear() === new Date().getFullYear()
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    ...(sameYear ? {} : { year: 'numeric' }),
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function AICoachHistoryPage() {
  const navigate = useNavigate()
  const {
    available,
    conversationId,
    listConversations,
    openConversation,
    deleteConversation,
    clearHistory,
    startNewChat,
  } = useAICoach()
  const [conversations, setConversations] = useState<CoachConversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [openingId, setOpeningId] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState<PendingDelete | null>(null)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setConversations(await listConversations())
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not load your AI Coach history.')
    } finally {
      setLoading(false)
    }
  }, [listConversations])

  useEffect(() => {
    if (available) void load()
  }, [available, load])

  async function open(conversation: CoachConversation) {
    setOpeningId(conversation.id)
    setError('')
    try {
      await openConversation(conversation.id)
      navigate('/coach')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not open that conversation.')
      setOpeningId(null)
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return
    setDeleting(true)
    setError('')
    try {
      if (pendingDelete.kind === 'all') {
        await clearHistory()
        setConversations([])
      } else {
        const { id } = pendingDelete.conversation
        await deleteConversation(id)
        setConversations((current) => current.filter((item) => item.id !== id))
      }
      setPendingDelete(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not delete that history.')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-4xl space-y-5 animate-fade-up">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-brand">
            <History size={16} /> AI Coach
          </p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-ink">Chat history</h1>
          <p className="mt-1 text-sm text-muted">Reopen a past conversation to read it or keep asking.</p>
        </div>
        <div className="flex gap-2">
          {conversations.length > 0 && (
            <Button type="button" variant="ghost" onClick={() => setPendingDelete({ kind: 'all' })}>
              <Trash2 size={16} /> Delete all
            </Button>
          )}
          <Button
            type="button"
            onClick={() => {
              startNewChat()
              navigate('/coach')
            }}
          >
            <Plus size={16} /> New chat
          </Button>
        </div>
      </header>

      {error && (
        <p role="alert" className="rounded-xl bg-bad-soft px-4 py-3 text-sm text-bad">
          {error}
        </p>
      )}

      {loading ? (
        <p role="status" className="flex items-center justify-center gap-2 py-16 text-sm text-muted">
          <Loader2 className="animate-spin text-brand" size={18} /> Loading history...
        </p>
      ) : conversations.length === 0 ? (
        <Card className="p-8 text-center">
          <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-brand-soft text-brand">
            <MessageSquare size={22} />
          </span>
          <h2 className="mt-4 text-lg font-bold text-ink">No saved chats yet</h2>
          <p className="mt-1 text-sm text-muted">Your AI Coach conversations will appear here.</p>
        </Card>
      ) : (
        <ul className="space-y-3" aria-label="Saved AI Coach conversations">
          {conversations.map((conversation) => {
            const skill = COACH_SKILLS.find((option) => option.value === conversation.skill) ?? COACH_SKILLS[0]
            const SkillIcon = skill.icon
            const active = conversation.id === conversationId
            return (
              <li key={conversation.id}>
                <Card className="flex items-center gap-2 !p-0">
                  <button
                    type="button"
                    onClick={() => void open(conversation)}
                    disabled={openingId !== null}
                    className="flex min-w-0 flex-1 items-center gap-3 rounded-card px-4 py-3.5 text-left transition hover:bg-surface-secondary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand disabled:cursor-wait sm:px-5"
                  >
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-soft text-brand">
                      {openingId === conversation.id ? <Loader2 className="animate-spin" size={18} /> : <SkillIcon size={18} />}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-ink">{conversation.title}</span>
                      <span className="mt-0.5 block text-xs text-muted">
                        {skill.label} · {conversation.message_count} messages · {formatUpdated(conversation.updated_at)}
                        {active && <span className="ml-1.5 font-semibold text-brand">· Current</span>}
                      </span>
                    </span>
                  </button>
                  <button
                    type="button"
                    aria-label={`Delete "${conversation.title}"`}
                    title="Delete"
                    onClick={() => setPendingDelete({ kind: 'one', conversation })}
                    className="mr-2 flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-muted transition hover:bg-bad-soft hover:text-bad focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
                  >
                    <Trash2 size={17} />
                  </button>
                </Card>
              </li>
            )
          })}
        </ul>
      )}

      {pendingDelete && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-4">
          <div role="dialog" aria-modal="true" aria-labelledby="delete-coach-title" className="w-full max-w-md rounded-card bg-surface p-5 shadow-elevated">
            <Trash2 className="text-bad" size={22} />
            <h2 id="delete-coach-title" className="mt-3 text-xl font-bold text-ink">
              {pendingDelete.kind === 'all' ? 'Delete all chat history?' : 'Delete this conversation?'}
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              {pendingDelete.kind === 'all'
                ? 'This permanently removes every AI Coach conversation from your account.'
                : `This permanently removes "${pendingDelete.conversation.title}".`}
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setPendingDelete(null)}>Cancel</Button>
              <Button type="button" variant="danger" disabled={deleting} onClick={() => void confirmDelete()}>
                {deleting ? <Loader2 className="animate-spin" size={17} /> : <Trash2 size={17} />} Delete
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
