import { Link } from 'react-router-dom'
import { CalendarClock, Compass, Target } from 'lucide-react'
import { Card, CardTitle, Meter } from '../../components/ui'
import { useAuth } from '../auth/AuthProvider'
import { SKILLS, type LearnerProfile } from '../auth/types'
import { countdownLabel, daysUntilExam } from '../../lib/countdown'

const SKILL_LABELS: Record<(typeof SKILLS)[number], string> = {
  listening: 'Listening',
  reading: 'Reading',
  writing: 'Writing',
  speaking: 'Speaking',
}

function CountdownCard({ profile }: { profile: LearnerProfile | null }) {
  const days = profile
    ? daysUntilExam(profile.exam_date, profile.timezone)
    : null

  return (
    <Card>
      <div className="flex items-start gap-3">
        <CalendarClock size={22} className="mt-0.5 shrink-0 text-accent" />
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
        <Target size={22} className="mt-0.5 shrink-0 text-accent" />
        <div>
          <CardTitle>Your target</CardTitle>
          {profile ? (
            <p className="mt-1 text-sm text-muted">
              Default target{' '}
              <span className="font-semibold text-ink">
                CELPIP {profile.target_level}
              </span>{' '}
              across all skills. Adjust per-skill targets in your{' '}
              <Link to="/account" className="font-semibold text-brand hover:underline">
                account
              </Link>
              .
            </p>
          ) : (
            <p className="mt-1 text-sm text-muted">
              Sign in and set a target level to track your readiness against a
              goal.
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
            ? 'Your countdown, targets, and per-skill readiness. Estimates appear here once you start practising.'
            : 'Preview of your study overview. Create an account to save an exam date, targets, and progress.'}
        </p>
      </header>

      {!isAuthed && (
        <Card className="border-brand/30 bg-brand-soft/40">
          <p className="text-sm text-ink">
            You are browsing without an account. Sample Learn and Practice pages
            are open to everyone, but saving a profile and progress needs a free
            account.{' '}
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

      <div>
        <h2 className="mb-3 text-lg font-semibold tracking-tight text-ink">
          Skill estimates
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {SKILLS.map((skill) => (
            <Card key={skill}>
              <div className="mb-2 flex items-center justify-between">
                <CardTitle>{SKILL_LABELS[skill]}</CardTitle>
                <span className="text-sm tabular-nums text-muted">—</span>
              </div>
              <Meter value={0} label={`${SKILL_LABELS[skill]} estimate: no data yet`} />
              <p className="mt-2 text-sm text-muted">No practice recorded yet.</p>
            </Card>
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardTitle className="mb-2">Overall readiness</CardTitle>
          <p className="text-sm text-muted">
            Readiness is a planning indicator, not a fifth CELPIP score. It will
            appear once there is enough practice across the four skills to be
            meaningful.
          </p>
        </Card>

        <Card>
          <div className="flex items-start gap-3">
            <Compass size={22} className="mt-0.5 shrink-0 text-accent" />
            <div>
              <CardTitle className="mb-2">Recommended next activity</CardTitle>
              <p className="text-sm text-muted">
                Start by understanding one task type end to end.
              </p>
              <p className="mt-2 text-sm">
                <Link to="/learn" className="font-semibold text-brand hover:underline">
                  Open Learn
                </Link>{' '}
                to explore the four skills, or{' '}
                <Link
                  to="/practice"
                  className="font-semibold text-brand hover:underline"
                >
                  browse Practice
                </Link>
                .
              </p>
            </div>
          </div>
        </Card>
      </div>
    </section>
  )
}
