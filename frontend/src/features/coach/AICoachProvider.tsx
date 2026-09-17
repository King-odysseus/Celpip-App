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
  messages: CoachMessage[]
  loading: boolean
  sending: boolean
  clearing: boolean
  clearOpen: boolean
  error: string
  openCoach: (options?: OpenCoachOptions) => void
  closeCoach: () => void
  toggleCoach: () => void
  setSkill: (skill: CoachSkill) => void
  setDraft: (draft: string) => void
  setClearOpen: (open: boolean) => void
  loadConversation: () => Promise<void>
  sendMessage: (question?: string) => Promise<void>
  clearConversation: () => Promise<void>
}

const AICoachContext = createContext<AICoachContextValue | null>(null)

export function AICoachProvider({ children }: { children: ReactNode }) {
  const { status, user } = useAuth()
  const available = status === 'authenticated'
  const [isOpen, setIsOpen] = useState(false)
  const [skill, setSkill] = useState<CoachSkill>('general')
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useState<CoachMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [sending, setSending] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [clearOpen, setClearOpen] = useState(false)
  const [error, setError] = useState('')
  const loadInFlight = useRef<Promise<void> | null>(null)

  useEffect(() => {
    setIsOpen(false)
    setMessages([])
    setLoaded(false)
    setLoading(false)
    setSending(false)
    setClearing(false)
    setClearOpen(false)
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
    setClearOpen(false)
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
      const reply = await api.post<CoachReply>('/me/ai-coach/', { message: content, skill })
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

  async function clearConversation() {
    if (!available || clearing) return
    setClearing(true)
    setError('')
    try {
      await api.del('/me/ai-coach/')
      setMessages([])
      setLoaded(true)
      setClearOpen(false)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not clear the conversation.')
    } finally {
      setClearing(false)
    }
  }

  const value = useMemo<AICoachContextValue>(
    () => ({
      available,
      isOpen,
      skill,
      draft,
      messages,
      loading,
      sending,
      clearing,
      clearOpen,
      error,
      openCoach,
      closeCoach,
      toggleCoach,
      setSkill,
      setDraft,
      setClearOpen,
      loadConversation,
      sendMessage,
      clearConversation,
    }),
    [
      available,
      isOpen,
      skill,
      draft,
      messages,
      loading,
      sending,
      clearing,
      clearOpen,
      error,
      openCoach,
      closeCoach,
      toggleCoach,
      loadConversation,
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
