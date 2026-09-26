import { Bot, RotateCcw, ShieldCheck } from 'lucide-react'
import { useEffect } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { AICoachClearDialog, AICoachConversation } from './AICoachConversation'
import { useAICoach } from './AICoachProvider'
import { COACH_SKILLS, isCoachSkill, STARTERS } from './coachData'

export function AICoachPage() {
  const [searchParams] = useSearchParams()
  const location = useLocation()
  const routeSkill = searchParams.get('skill')
  const routedPrompt = (location.state as { coachPrompt?: unknown } | null)?.coachPrompt
  const {
    available,
    skill,
    messages,
    setSkill,
    setDraft,
    setClearOpen,
    loadConversation,
  } = useAICoach()

  useEffect(() => {
    if (isCoachSkill(routeSkill)) setSkill(routeSkill)
  }, [routeSkill, setSkill])

  useEffect(() => {
    if (typeof routedPrompt === 'string') setDraft(routedPrompt)
  }, [routedPrompt, setDraft])

  useEffect(() => {
    if (available) void loadConversation()
  }, [available, loadConversation])

  function chooseStarter(prompt: string) {
    setDraft(prompt)
    document.getElementById('coach-page-question')?.focus()
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
        <Card className="flex h-[clamp(26rem,calc(100dvh-13rem),48rem)] flex-col overflow-hidden !p-0">
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

          <AICoachConversation />
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

      <AICoachClearDialog />
    </div>
  )
}
