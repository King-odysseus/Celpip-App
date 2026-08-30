import { Link } from 'react-router-dom'
import { CalendarClock, Target } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Card, CardTitle } from '../../components/ui'
import { api } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'
import type { LearnerProfile } from '../auth/types'
import { countdownLabel, daysUntilExam } from '../../lib/countdown'
import type { Dashboard } from '../learning/types'
import { DashboardStats } from './DashboardStats'
import { TodayTasks } from './TodayTasks'
import { SkillEstimates } from './SkillEstimates'
import { SkillSignals } from './SkillSignals'
import { RecentResults } from './RecentResults'
import { ReadinessIndicator } from './ReadinessIndicator'
import { FeedbackHistory } from './FeedbackHistory'

function CountdownCard({ profile }: { profile: LearnerProfile | null }) {
  const days = profile ? daysUntilExam(profile.exam_date, profile.timezone) : null

  return (
    <Card>
      <div className="flex items-start gap-3">
        <CalendarClock size={22} className="mt-0.5 shrink-0 text-accent" aria-hidden />
        <div className="min-w-0">
          <CardTitle>Exam countdown</CardTitle>
          {days === null ? (
            <p className="mt-1 text-sm text-muted">
              No exam date set yet.{' '}
              <Link to="/account" className="font-semibold text-brand hover:underline">
                Set your exam date
              </Link>{' '}
              to start the countdown.
            </p>
          ) : (
            <>
              <p className="mt-1 text-3xl font-semibold tracking-tight tabular-nums text-ink">
                {countdownLabel(days)}
              </p>
              <p className="mt-0.5 text-sm text-muted">
                Exam date: <span className="tabular-nums">{profile?.exam_date}</span>
              </p>
            </>
          )}
        </div>
      </div>
    </Card>
  )
}

function TargetCard({ profile }: { profile: LearnerProfile | null }) {
  return (
    <Card>
      <div className="flex items-start gap-3">
        <Target size={22} className="mt-0.5 shrink-0 text-accent" aria-hidden />
        <div>
          <CardTitle>Your target</CardTitle>
          {profile ? (
            <p className="mt-1 text-sm text-muted">
              Default target{' '}
              <span className="font-semibold text-ink">CELPIP {profile.target_level}</span>{' '}
              across all skills. Adjust per-skill targets in your{' '}
              <Link to="/account" className="font-semibold text-brand hover:underline">
                account
              </Link>
              .
            </p>
          ) : (
            <p className="mt-1 text-sm text-muted">
              Sign in and set a target level to track your readiness against a goal.
            </p>
          )}
        </div>
      </div>
    </Card>
  )
}

export function DashboardPage() {
  const { status, profile } = useAuth()
  const isAuthed = status === 'authenticated'
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isAuthed) {
      setDashboard(null)
      setError('')
      return
    }
    let active = true
    api
      .get<Dashboard>('/me/dashboard/')
      .then((data) => {
        if (active) setDashboard(data)
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(
            reason instanceof Error ? reason.message : 'Could not load your dashboard.',
          )
        }
      })
    return () => {
      active = false
    }
  }, [isAuthed])

  return (
    <section aria-labelledby="dashboard-title" className="space-y-6">
      <header className="space-y-1.5">
        <p className="eyebrow">Overview</p>
        <h1
          id="dashboard-title"
          className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl"
        >
          Dashboard
        </h1>
        <p className="max-w-2xl text-sm text-muted sm:text-base">
          {isAuthed
            ? 'Your countdown, targets, streak, today\u2019s work, recent results, and a transparent practice planning indicator.'
            : 'Preview of your study overview. Create an account to save an exam date, targets, and progress.'}
        </p>
      </header>

      {!isAuthed && (
        <Card className="border-brand/30 bg-brand-soft/40">
          <p className="text-sm text-ink">
            You are browsing without an account. Sample Learn and Practice pages are open
            to everyone, but saving a profile and progress needs a free account.{' '}
            <Link to="/register" className="font-semibold text-brand hover:underline">
              Create one
            </Link>{' '}
            or{' '}
            <Link to="/signin" className="font-semibold text-brand hover:underline">
              sign in
            </Link>
            .
          </p>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <CountdownCard profile={profile} />
        <TargetCard profile={profile} />
      </div>

      {isAuthed &&
        (error ? (
          <p role="alert" className="rounded-input bg-bad-soft p-3 text-bad">
            {error}
          </p>
        ) : !dashboard ? (
          <p role="status" className="py-16 text-center text-muted">
            Loading your dashboard…
          </p>
        ) : (
          <>
            <DashboardStats
              streakDays={dashboard.streak.days}
              totalQuestions={dashboard.totals.objective_questions_completed}
              completedAttempts={dashboard.totals.completed_attempts}
            />
            <TodayTasks
              date={dashboard.today.date}
              tasks={dashboard.today.tasks}
              nextUpcoming={dashboard.next_upcoming_task}
            />
            <SkillEstimates skills={dashboard.skills} />
            <SkillSignals signals={dashboard.signals} />
            <RecentResults results={dashboard.recent_results} />
            <FeedbackHistory />
            <ReadinessIndicator readiness={dashboard.readiness} />
          </>
        ))}
    </section>
  )
}
