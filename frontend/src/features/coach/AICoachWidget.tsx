import { Bot, ChevronDown, History, Maximize2, MessageCircleQuestion, RotateCcw } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { COACH_SKILLS } from './coachData'
import { AICoachConversation } from './AICoachConversation'
import { useAICoach } from './AICoachProvider'

export function AICoachWidget() {
  const location = useLocation()
  const launcherRef = useRef<HTMLButtonElement>(null)
  const {
    available,
    isOpen,
    skill,
    messages,
    openCoach,
    closeCoach,
    setSkill,
    startNewChat,
  } = useAICoach()

  useEffect(() => {
    if (location.pathname.startsWith('/coach') && isOpen) closeCoach()
  }, [closeCoach, isOpen, location.pathname])

  useEffect(() => {
    if (!isOpen) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      event.preventDefault()
      closeCoach()
      window.setTimeout(() => launcherRef.current?.focus(), 0)
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [closeCoach, isOpen])

  if (!available || location.pathname.startsWith('/coach')) return null

  if (!isOpen) {
    return (
      <button
        ref={launcherRef}
        type="button"
        aria-label="Open AI Coach"
        aria-haspopup="dialog"
        onClick={() => openCoach()}
        className="fixed right-4 bottom-[calc(6.25rem+env(safe-area-inset-bottom))] z-40 flex h-14 w-14 items-center justify-center rounded-full bg-brand text-white shadow-elevated transition hover:scale-105 hover:bg-brand/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand lg:right-6 lg:bottom-6"
      >
        <MessageCircleQuestion size={25} strokeWidth={2} />
      </button>
    )
  }

  const activeSkill = COACH_SKILLS.find((option) => option.value === skill) ?? COACH_SKILLS[0]

  return (
    <>
      <section
        role="dialog"
        aria-labelledby="ai-coach-widget-title"
        className="fixed inset-x-3 bottom-[calc(6.25rem+env(safe-area-inset-bottom))] z-50 flex h-[min(36rem,calc(100dvh-8rem))] flex-col overflow-hidden rounded-3xl bg-surface shadow-elevated lg:inset-x-auto lg:right-6 lg:bottom-6 lg:h-[min(38rem,calc(100dvh-3rem))] lg:w-[24rem]"
      >
        <header className="flex min-h-16 items-center gap-2 bg-brand px-3.5 py-3 text-white">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/15">
            <Bot size={20} />
          </span>
          <div className="min-w-0 flex-1">
            <h2 id="ai-coach-widget-title" className="truncate text-sm font-bold">AI Coach</h2>
            <p className="truncate text-xs text-white/75">{activeSkill.label} focus</p>
          </div>
          {messages.length > 0 && (
            <button
              type="button"
              aria-label="New chat"
              title="New chat"
              onClick={startNewChat}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-white/80 transition hover:bg-white/15 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            >
              <RotateCcw size={17} />
            </button>
          )}
          <Link
            to="/coach/history"
            aria-label="AI Coach history"
            title="History"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-white/80 transition hover:bg-white/15 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            <History size={17} />
          </Link>
          <Link
            to={skill === 'general' ? '/coach' : `/coach?skill=${skill}`}
            aria-label="Open full AI Coach"
            title="Open full AI Coach"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-white/80 transition hover:bg-white/15 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            <Maximize2 size={17} />
          </Link>
          <button
            type="button"
            aria-label="Minimize AI Coach"
            title="Minimize"
            onClick={() => {
              closeCoach()
              window.setTimeout(() => launcherRef.current?.focus(), 0)
            }}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-white/80 transition hover:bg-white/15 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            <ChevronDown size={20} />
          </button>
        </header>

        <div className="scrollbar-none flex gap-1.5 overflow-x-auto px-3 py-2.5 [mask-image:linear-gradient(to_right,transparent,black_0.75rem,black_calc(100%-1.5rem),transparent)]">
          {COACH_SKILLS.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              type="button"
              aria-pressed={skill === value}
              onClick={() => setSkill(value)}
              className={`flex min-h-9 shrink-0 items-center gap-1.5 rounded-full px-3 text-xs font-semibold transition ${
                skill === value
                  ? 'bg-brand text-white'
                  : 'bg-surface-secondary text-muted hover:text-ink'
              }`}
            >
              <Icon size={14} /> {label}
            </button>
          ))}
        </div>

        <AICoachConversation compact autoFocus />
        <p className="px-3 pb-2.5 text-center text-[11px] leading-4 text-muted">
          Practice guidance only. Not an official CELPIP score.
        </p>
      </section>
    </>
  )
}
