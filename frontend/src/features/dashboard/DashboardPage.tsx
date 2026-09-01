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
import { NextBestSession } from './NextBestSession'
import { BaselineAssessment } from './BaselineAssessment'

function CountdownCard({ profile }: { profile: LearnerProfile | null }) {
  const days = profile ? daysUntilExam(profile.exam_date, profile.timezone) : null

  return (
    <Card className="!p-4 min-h-[108px]">
      <div className="flex h-full items-start gap-2.5">
        <CalendarClock size={19} className="mt-0.5 shrink-0 text-accent" aria-hidden />
        <div className="min-w-0">
          <CardTitle className="text-sm">Exam countdown</CardTitle>
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
              <p className="mt-1 text-2xl font-semibold tracking-tight tabular-nums text-ink">
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
    <Card className="!p-4 min-h-[108px]">
      <div className="flex h-full items-start gap-2.5">
        <Target size={19} className="mt-0.5 shrink-0 text-accent" aria-hidden />
        <div className="min-w-0">
          <CardTitle className="text-sm">Your target</CardTitle>
          {profile ? (
            <>
              <p className="mt-1 text-xl font-semibold tracking-tight text-ink">CELPIP {profile.target_level}</p>
              <p className="mt-0.5 text-xs text-muted">
              Default across all skills ·{' '}
              <Link to="/account" className="font-semibold text-brand hover:underline">
                Adjust in account
              </Link>
              .
              </p>
            </>
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
          ? 'See how prepared your practice data suggests you are, where you are strongest, and what to work on next.'
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

      {isAuthed && dashboard && (
        <>
          <NextBestSession dashboard={dashboard} />
          <BaselineAssessment skills={dashboard.skills} />
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <CountdownCard profile={profile} />
            <TargetCard profile={profile} />
            <DashboardStats
              streakDays={dashboard.streak.days}
              totalQuestions={dashboard.totals.objective_questions_completed}
              completedAttempts={dashboard.totals.completed_attempts}
            />
          </div>
          <TodayTasks
            date={dashboard.today.date}
            tasks={dashboard.today.tasks}
            nextUpcoming={dashboard.next_upcoming_task}
          />
          <SkillEstimates skills={dashboard.skills} />
          <ReadinessIndicator readiness={dashboard.readiness} />
        </>
      )}

      {!isAuthed && (
        <div className="grid gap-3 sm:grid-cols-2">
          <CountdownCard profile={profile} />
          <TargetCard profile={profile} />
        </div>
      )}

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
            <SkillSignals signals={dashboard.signals} />
            <RecentResults results={dashboard.recent_results} />
            <FeedbackHistory />
          </>
        ))}
    </section>
  )
}
