import { ArrowRight, BookOpen, CheckCircle2, Headphones, Mic, PenLine } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, CardTitle } from '../../components/ui'
import { AccountRequired } from '../learning/ProgressPage'
import { useAuth } from '../auth/AuthProvider'
import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { Skill } from '../learning/types'
import { SKILL_LABELS } from './labels'

const skills: Array<{ skill: Skill; Icon: typeof BookOpen; description: string }> = [
  { skill: 'listening', Icon: Headphones, description: 'Measure how well you follow purpose, detail, and viewpoints.' },
  { skill: 'reading', Icon: BookOpen, description: 'Measure information retrieval, inference, and viewpoint understanding.' },
  { skill: 'writing', Icon: PenLine, description: 'Create a writing baseline using the task rubric and word target.' },
  { skill: 'speaking', Icon: Mic, description: 'Record a response and reflect on clarity, structure, and delivery.' },
]

function pathFor(skill: Skill): string {
  return (skill === 'reading' ? '/practice' : `/practice/${skill}`) + '?diagnostic=1'
}

type DiagnosticSkill = {
  skill: Skill
  status: 'completed' | 'in_progress'
  session_id: string
  started_at: string
  completed_at: string | null
  title: string
  accuracy_percent: number | null
}

type DiagnosticReport = {
  skills: DiagnosticSkill[]
  completed: number
  total: number
  is_complete: boolean
  recommendation: { skill: Skill | null; title: string; reason: string; destination: string }
  disclaimer: string
}

export function DiagnosticPage() {
  const { status } = useAuth()
  const [report, setReport] = useState<DiagnosticReport | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    if (status !== 'authenticated') return
    let active = true
    api.get<DiagnosticReport>('/me/diagnostic/')
      .then((data) => active && setReport(data))
      .catch(() => active && setError('Your baseline report could not be loaded yet.'))
    return () => { active = false }
  }, [status])
  if (status === 'loading') return <p role="status" className="py-16 text-center text-muted">Loading your baseline…</p>
  if (status !== 'authenticated') return <AccountRequired title="Baseline assessment" />
  const bySkill = new Map(report?.skills.map((item) => [item.skill, item]) ?? [])
  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 animate-fade-up">
      <header className="rounded-card bg-brand px-5 py-8 text-white shadow-elevated sm:px-8">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent-soft">Your starting point</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Baseline assessment</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-white/80 sm:text-base">
          Complete one untimed activity in each skill. These first attempts establish evidence for your study plan; they are not an official CELPIP score.
        </p>
      </header>
      <Card className="border-info/30 bg-info-bg p-5">
        <CardTitle>How it works</CardTitle>
        <ol className="mt-3 grid gap-3 text-sm leading-6 text-ink sm:grid-cols-3">
          <li><strong>1. Choose a skill.</strong><br />Start with the area you want to understand first.</li>
          <li><strong>2. Complete one activity.</strong><br />Work carefully; the goal is useful evidence, not speed.</li>
          <li><strong>3. Return for guidance.</strong><br />Your dashboard will show coverage and the next recommended action.</li>
        </ol>
      </Card>
      {error && <p role="alert" className="rounded-input bg-bad-soft p-3 text-sm text-bad">{error}</p>}
      <Card className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><p className="eyebrow">Your progress</p><CardTitle className="mt-1">{report?.is_complete ? 'Baseline complete' : 'Build your four-skill picture'}</CardTitle></div>
          <span className="rounded-full bg-accent-soft px-3 py-1.5 text-xs font-bold tabular-nums text-brand">{report?.completed ?? 0}/4 complete</span>
        </div>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-line" aria-label={`${report?.completed ?? 0} of 4 baseline skills complete`} role="progressbar" aria-valuemin={0} aria-valuemax={4} aria-valuenow={report?.completed ?? 0}>
          <div className="h-full rounded-full bg-good transition-all" style={{ width: `${((report?.completed ?? 0) / 4) * 100}%` }} />
        </div>
        {report?.is_complete && <p className="mt-3 text-sm leading-6 text-muted">Your baseline is ready. Review the evidence below, then use your dashboard for a targeted study recommendation.</p>}
      </Card>
      {report?.recommendation && (
        <Card className="border-brand/30 bg-brand-soft/30 p-5">
          <p className="eyebrow">Recommended next step</p>
          <CardTitle className="mt-1">{report.recommendation.title}</CardTitle>
          <p className="mt-2 text-sm leading-6 text-muted">{report.recommendation.reason}</p>
          <Link to={report.recommendation.destination} className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-full bg-brand px-4 py-2 text-sm font-semibold text-white hover:opacity-90">
            {report.recommendation.destination === '/study-plan' ? 'Open study plan' : 'Continue baseline'} <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </Card>
      )}
      <section aria-labelledby="baseline-skills-title">
        <h2 id="baseline-skills-title" className="text-2xl font-bold text-ink">Choose your first baseline</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {skills.map(({ skill, Icon, description }) => {
            const entry = bySkill.get(skill)
            const complete = entry?.status === 'completed'
            return (
            <Card key={skill} className="flex flex-col p-5">
              <div className="flex items-start gap-3">
                <Icon size={22} className="mt-0.5 shrink-0 text-accent" aria-hidden />
                <div><h3 className="text-lg font-bold text-ink">{SKILL_LABELS[skill]}</h3><p className="mt-1 text-sm leading-6 text-muted">{description}</p></div>
              </div>
              {complete && <p className="mt-4 text-sm font-semibold text-good">Completed{entry.accuracy_percent !== null ? ` · ${entry.accuracy_percent}% objective accuracy` : ''}</p>}
              <Link to={pathFor(skill)} className="mt-5 inline-flex min-h-11 items-center justify-center gap-2 rounded-full bg-brand px-4 py-2 text-sm font-semibold text-white hover:opacity-90">
                {entry?.status === 'in_progress' ? 'Continue' : complete ? 'Retake baseline' : `Start ${SKILL_LABELS[skill]}`} <ArrowRight size={16} aria-hidden="true" />
              </Link>
            </Card>
            )
          })}
        </div>
      </section>
      <p className="flex items-start gap-2 text-xs leading-5 text-muted"><CheckCircle2 size={15} className="mt-0.5 shrink-0 text-good" aria-hidden /> {report?.disclaimer ?? 'You can complete these in any order. Existing practice history remains separate and is never rewritten.'}</p>
    </div>
  )
}
