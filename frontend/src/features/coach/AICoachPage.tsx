import {
  BookOpen,
  Bot,
  Headphones,
  Loader2,
  Mic2,
  PenLine,
  RotateCcw,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  type LucideIcon,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { api } from '../../lib/api'
import type { Skill } from '../auth/types'

type CoachSkill = 'general' | Skill

type CoachMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  skill: CoachSkill
  created_at: string
}

type CoachThread = { messages: CoachMessage[] }
type CoachReply = { user_message: CoachMessage; coach_message: CoachMessage }

const COACH_SKILLS: Array<{ value: CoachSkill; label: string; icon: LucideIcon }> = [
  { value: 'general', label: 'All skills', icon: Sparkles },
  { value: 'listening', label: 'Listening', icon: Headphones },
  { value: 'reading', label: 'Reading', icon: BookOpen },
  { value: 'writing', label: 'Writing', icon: PenLine },
  { value: 'speaking', label: 'Speaking', icon: Mic2 },
]

const STARTERS: Record<CoachSkill, string[]> = {
  general: [
    'What should I focus on to improve my overall score?',
    'How should I review a practice attempt so it actually helps?',
    'What is a realistic weekly practice routine for 30 minutes a day?',
  ],
  listening: [
    'How can I keep up with fast conversations?',
    'What should I write down while listening?',
    'How do I handle a question when I miss one detail?',
  ],
  reading: [
    'How can I find the right evidence faster?',
    'What should I do when two answer choices look correct?',
    'How can I manage the reading time limit?',
  ],
  writing: [
    'How should I structure a CELPIP email?',
    'How can I make my survey response more specific?',
    'How do I improve vocabulary without sounding unnatural?',
  ],
  speaking: [
    'How can I speak for the full response time?',
    'What structure works for a difficult-situation task?',
    'How can I reduce long pauses?',
  ],
}

function isCoachSkill(value: string | null): value is CoachSkill {
  return COACH_SKILLS.some((option) => option.value === value)
}

export function AICoachPage() {
  const [searchParams] = useSearchParams()
  const location = useLocation()
  const routeSkill = searchParams.get('skill')
  const routedPrompt = (location.state as { coachPrompt?: unknown } | null)?.coachPrompt
  const [skill, setSkill] = useState<CoachSkill>(isCoachSkill(routeSkill) ? routeSkill : 'general')
  const [messages, setMessages] = useState<CoachMessage[]>([])
  const [draft, setDraft] = useState(
    typeof routedPrompt === 'string' ? routedPrompt : '',
  )
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [clearOpen, setClearOpen] = useState(false)
  const [clearing, setClearing] = useState(false)
  const logEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (isCoachSkill(routeSkill)) setSkill(routeSkill)
  }, [routeSkill])

  useEffect(() => {
    let active = true
    api
      .get<CoachThread>('/me/ai-coach/')
      .then((thread) => {
        if (active) setMessages(thread.messages)
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : 'Could not load your conversation.')
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (typeof logEndRef.current?.scrollIntoView === 'function') {
      logEndRef.current.scrollIntoView({ block: 'end' })
    }
  }, [messages, sending])

  async function sendMessage(question = draft) {
    const content = question.trim()
    if (!content || sending) return

    const optimistic: CoachMessage = {
      id: `local-${Date.now()}`,
      role: 'user',
      content,
      skill,
      created_at: new Date().toISOString(),
    }
    setMessages((current) => [...current, optimistic])
    setDraft('')
    setError('')
    setSending(true)
    try {
      const reply = await api.post<CoachReply>('/me/ai-coach/', { message: content, skill })
      setMessages((current) => [
        ...current.filter((message) => message.id !== optimistic.id),
        reply.user_message,
        reply.coach_message,
      ])
    } catch (reason) {
      setMessages((current) => current.filter((message) => message.id !== optimistic.id))
      setDraft(content)
      setError(reason instanceof Error ? reason.message : 'The AI Coach could not answer.')
    } finally {
      setSending(false)
      window.setTimeout(() => textareaRef.current?.focus(), 0)
    }
  }

  async function clearConversation() {
    setClearing(true)
    setError('')
    try {
      await api.del('/me/ai-coach/')
      setMessages([])
      setClearOpen(false)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not clear the conversation.')
    } finally {
      setClearing(false)
    }
  }

  function chooseStarter(prompt: string) {
    setDraft(prompt)
    textareaRef.current?.focus()
  }

  const activeSkill = COACH_SKILLS.find((option) => option.value === skill) ?? COACH_SKILLS[0]

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5 animate-fade-up">
      <header className="rounded-card bg-brand px-5 py-7 text-white shadow-elevated sm:px-8">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-accent-soft">
          <Bot size={17} /> AI Coach
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Ask before your next attempt</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-white/80 sm:text-base">
          Get focused advice on how to answer, what to improve, and what to practise next.
        </p>
      </header>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Card className="flex min-h-[34rem] flex-col overflow-hidden !p-0">
          <div className="flex items-center justify-between gap-3 border-b border-line-light px-4 py-3 sm:px-5">
            <div className="min-w-0">
              <p className="text-sm font-bold text-ink">{activeSkill.label} focus</p>
              <p className="truncate text-xs text-muted">Your conversation stays in your account.</p>
            </div>
            {messages.length > 0 && (
              <Button
                type="button"
                variant="ghost"
                className="shrink-0 px-3"
                onClick={() => setClearOpen(true)}
              >
                <RotateCcw size={16} /> New chat
              </Button>
            )}
          </div>

          <div
            role="log"
            aria-live="polite"
            aria-label="AI Coach conversation"
            className="flex-1 space-y-4 overflow-y-auto px-4 py-5 sm:px-5"
          >
            {loading && (
              <p role="status" className="flex items-center justify-center gap-2 py-16 text-sm text-muted">
                <Loader2 className="animate-spin text-brand" size={18} /> Loading conversation...
              </p>
            )}

            {!loading && messages.length === 0 && (
              <div className="mx-auto max-w-xl py-8 text-center">
                <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-brand-soft text-brand">
                  <Bot size={24} />
                </span>
                <h2 className="mt-4 text-xl font-bold text-ink">What would you like to improve?</h2>
                <p className="mt-2 text-sm leading-6 text-muted">
                  Ask a specific question, or choose a starting point from the practice focus panel.
                </p>
              </div>
            )}

            {messages.map((message) => (
              <article
                key={message.id}
                className={message.role === 'user' ? 'ml-auto max-w-[88%]' : 'mr-auto max-w-[92%]'}
              >
                <p className={`mb-1 text-xs font-bold uppercase tracking-wide ${message.role === 'user' ? 'text-right text-muted' : 'text-brand'}`}>
                  {message.role === 'user' ? 'You' : 'AI Coach'}
                </p>
                <div
                  className={`rounded-2xl px-4 py-3 text-sm leading-6 ${
                    message.role === 'user'
                      ? 'rounded-br-md bg-brand text-white'
                      : 'rounded-bl-md bg-surface-secondary text-ink'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
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
            className="border-t border-line-light bg-surface p-3 sm:p-4"
            onSubmit={(event) => {
              event.preventDefault()
              void sendMessage()
            }}
          >
            {error && (
              <p role="alert" className="mb-3 rounded-xl bg-bad-soft px-3 py-2 text-sm text-bad">
                {error}
              </p>
            )}
            <div className="flex items-end gap-2 rounded-2xl border border-line bg-surface-secondary p-2 focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/15">
              <label htmlFor="coach-question" className="sr-only">Message the AI Coach</label>
              <textarea
                ref={textareaRef}
                id="coach-question"
                value={draft}
                maxLength={2000}
                rows={2}
                placeholder="Ask a direct question about improving or answering a task..."
                className="max-h-40 min-h-12 flex-1 resize-none bg-transparent px-2 py-2 text-sm leading-6 text-ink outline-none placeholder:text-muted"
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
                className="h-11 w-11 shrink-0 !p-0"
              >
                {sending ? <Loader2 className="animate-spin" size={19} /> : <Send size={19} />}
              </Button>
            </div>
          </form>
        </Card>

        <aside className="space-y-4">
          <Card className="p-5">
            <h2 className="text-sm font-bold text-ink">Practice focus</h2>
            <div className="mt-3 grid grid-cols-2 gap-2 lg:grid-cols-1">
              {COACH_SKILLS.map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={skill === value}
                  onClick={() => setSkill(value)}
                  className={`flex min-h-11 items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-semibold transition ${
                    skill === value
                      ? 'bg-brand text-white'
                      : 'bg-surface-secondary text-ink hover:bg-brand-soft'
                  }`}
                >
                  <Icon size={17} /> {label}
                </button>
              ))}
            </div>
          </Card>

          <Card className="p-5">
            <h2 className="text-sm font-bold text-ink">Try asking</h2>
            <div className="mt-3 space-y-2">
              {STARTERS[skill].map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => chooseStarter(prompt)}
                  className="w-full rounded-xl bg-surface-secondary px-3 py-3 text-left text-sm leading-5 text-ink transition hover:bg-brand-soft hover:text-brand"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </Card>

          <Card className="border-accent/30 bg-accent-soft/20 p-4">
            <p className="flex items-start gap-2 text-xs leading-5 text-muted">
              <ShieldCheck className="mt-0.5 shrink-0 text-good" size={16} />
              Practice guidance only. AI Coach answers are not official CELPIP scores or guaranteed results.
            </p>
          </Card>
        </aside>
      </div>

      {clearOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
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
      )}
    </div>
  )
}
