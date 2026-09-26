import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'
import {
  isCoachSkill,
  type CoachConversation,
  type CoachConversationList,
  type CoachMessage,
  type CoachReply,
  type CoachSkill,
  type CoachThread,
} from './coachData'

type OpenCoachOptions = {
  skill?: CoachSkill
  prompt?: string
}

type AICoachContextValue = {
  available: boolean
  isOpen: boolean
  skill: CoachSkill
  draft: string
  conversationId: string | null
  messages: CoachMessage[]
  loading: boolean
  sending: boolean
  error: string
  openCoach: (options?: OpenCoachOptions) => void
  closeCoach: () => void
  toggleCoach: () => void
  setSkill: (skill: CoachSkill) => void
  setDraft: (draft: string) => void
  loadConversation: () => Promise<void>
  sendMessage: (question?: string) => Promise<void>
  startNewChat: () => void
  listConversations: () => Promise<CoachConversation[]>
  openConversation: (id: string) => Promise<void>
  deleteConversation: (id: string) => Promise<void>
  clearHistory: () => Promise<void>
}

const AICoachContext = createContext<AICoachContextValue | null>(null)

export function AICoachProvider({ children }: { children: ReactNode }) {
  const { status, user } = useAuth()
  const available = status === 'authenticated'
  const [isOpen, setIsOpen] = useState(false)
  const [skill, setSkill] = useState<CoachSkill>('general')
  const [draft, setDraft] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<CoachMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const loadInFlight = useRef<Promise<void> | null>(null)

  useEffect(() => {
    setIsOpen(false)
    setConversationId(null)
    setMessages([])
    setLoaded(false)
    setLoading(false)
    setSending(false)
    setError('')
  }, [available, user?.id])

  const loadConversation = useCallback(async () => {
    if (!available || loaded) return
    if (loadInFlight.current) return loadInFlight.current

    const pending = (async () => {
      setLoading(true)
      setError('')
      try {
        const thread = await api.get<CoachThread>('/me/ai-coach/')
        setConversationId(thread.conversation?.id ?? null)
        setMessages(thread.messages)
        setLoaded(true)
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'Could not load your conversation.')
      } finally {
        setLoading(false)
      }
    })()
    loadInFlight.current = pending
    try {
      await pending
    } finally {
      loadInFlight.current = null
    }
  }, [available, loaded])

  const openCoach = useCallback(
    (options?: OpenCoachOptions) => {
      if (!available) return
      if (options?.skill) setSkill(options.skill)
      if (typeof options?.prompt === 'string') setDraft(options.prompt)
      setError('')
      setIsOpen(true)
      void loadConversation()
    },
    [available, loadConversation],
  )

  const closeCoach = useCallback(() => {
    setIsOpen(false)
  }, [])

  const toggleCoach = useCallback(() => {
    if (isOpen) closeCoach()
    else openCoach()
  }, [closeCoach, isOpen, openCoach])

  async function sendMessage(question = draft) {
    const content = question.trim()
    if (!available || !content || sending) return

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
      const reply = await api.post<CoachReply>('/me/ai-coach/', {
        message: content,
        skill,
        ...(conversationId ? { conversation_id: conversationId } : {}),
      })
      setConversationId(reply.conversation.id)
      setMessages((current) => [
        ...current.filter((message) => message.id !== optimistic.id),
        reply.user_message,
        reply.coach_message,
      ])
      setLoaded(true)
    } catch (reason) {
      setMessages((current) => current.filter((message) => message.id !== optimistic.id))
      setDraft(content)
      setError(reason instanceof Error ? reason.message : 'The AI Coach could not answer.')
    } finally {
      setSending(false)
    }
  }

  // Starting a new chat only resets local state; the previous chat stays in
  // history and the next question creates a new saved conversation.
  const startNewChat = useCallback(() => {
    setConversationId(null)
    setMessages([])
    setDraft('')
    setError('')
    setLoaded(true)
  }, [])

  const listConversations = useCallback(async () => {
    const list = await api.get<CoachConversationList>('/me/ai-coach/conversations/')
    return list.results
  }, [])

  const openConversation = useCallback(async (id: string) => {
    const thread = await api.get<CoachThread>(`/me/ai-coach/conversations/${id}/`)
    setConversationId(thread.conversation?.id ?? id)
    setMessages(thread.messages)
    if (thread.conversation && isCoachSkill(thread.conversation.skill)) {
      setSkill(thread.conversation.skill)
    }
    setError('')
    setLoaded(true)
  }, [])

  const deleteConversation = useCallback(
    async (id: string) => {
      await api.del(`/me/ai-coach/conversations/${id}/`)
      if (id === conversationId) startNewChat()
    },
    [conversationId, startNewChat],
  )

  const clearHistory = useCallback(async () => {
    await api.del('/me/ai-coach/')
    startNewChat()
  }, [startNewChat])

  const value = useMemo<AICoachContextValue>(
    () => ({
      available,
      isOpen,
      skill,
      draft,
      conversationId,
      messages,
      loading,
      sending,
      error,
      openCoach,
      closeCoach,
      toggleCoach,
      setSkill,
      setDraft,
      loadConversation,
      sendMessage,
      startNewChat,
      listConversations,
      openConversation,
      deleteConversation,
      clearHistory,
    }),
    [
      available,
      isOpen,
      skill,
      draft,
      conversationId,
      messages,
      loading,
      sending,
      error,
      openCoach,
      closeCoach,
      toggleCoach,
      loadConversation,
      startNewChat,
      listConversations,
      openConversation,
      deleteConversation,
      clearHistory,
    ],
  )

  return <AICoachContext.Provider value={value}>{children}</AICoachContext.Provider>
}

export function useAICoach(): AICoachContextValue {
  const context = useContext(AICoachContext)
  if (!context) throw new Error('useAICoach must be used within an AICoachProvider')
  return context
}

export function AICoachTrigger({
  skill = 'general',
  prompt,
  className,
  children,
}: {
  skill?: CoachSkill
  prompt?: string
  className?: string
  children: ReactNode
}) {
  const coach = useContext(AICoachContext)
  if (!coach?.available) {
    return (
      <Link
        to={skill === 'general' ? '/coach' : `/coach?skill=${skill}`}
        state={prompt ? { coachPrompt: prompt } : undefined}
        className={className}
      >
        {children}
      </Link>
    )
  }

  return (
    <button
      type="button"
      className={className}
      onClick={() => coach.openCoach({ skill: isCoachSkill(skill) ? skill : 'general', prompt })}
    >
      {children}
    </button>
  )
}
