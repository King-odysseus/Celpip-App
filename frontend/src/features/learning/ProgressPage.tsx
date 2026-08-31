import { BarChart3, ShieldCheck, Target } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, Meter } from '../../components/ui'
import { api } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'
import type { Progress, Skill } from './types'

const labels: Record<Skill, string> = { listening: 'Listening', reading: 'Reading', writing: 'Writing', speaking: 'Speaking' }

export function ProgressPage() {
  const { status } = useAuth()
  const [progress, setProgress] = useState<Progress | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    if (status !== 'authenticated') return
    api.get<Progress>('/me/progress/').then(setProgress).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Could not load progress.'))
  }, [status])

  if (status === 'loading') return <p role="status" className="py-16 text-center text-muted">Loading progress…</p>
  if (status !== 'authenticated') return <AccountRequired title="Progress" />
  return (
    <div className="mx-auto w-full max-w-[1600px] space-y-7 animate-fade-up">
      <header><p className="eyebrow">Evidence, not guesswork</p><h1 className="mt-1 text-3xl font-bold text-ink">Progress</h1><p className="mt-2 max-w-3xl text-muted">Objective accuracy and AI-assisted Writing/Speaking ranges stay separate so you can see what each measure actually means.</p></header>
      {error && <p role="alert" className="rounded-input bg-bad-soft p-3 text-bad">{error}</p>}
      {!progress ? <p role="status" className="py-10 text-center text-muted">Building your progress view…</p> : <>
        {progress.target_guidance?.some((item) => item.attained === false) && (
          <Card className="border-warning/40 bg-warning-soft/30 p-5">
            <h2 className="text-xl font-bold text-ink">Your target needs another attempt</h2>
            <p className="mt-2 text-sm leading-6 text-muted">These are unofficial practice estimates, not official CELPIP results. Review the tips, then take the recommended test again.</p>
            <div className="mt-4 space-y-4">
              {progress.target_guidance.filter((item) => item.attained === false).map((item) => (
                <div key={item.skill} className="rounded-input border border-line bg-surface p-4">
                  <p className="font-bold text-ink">{labels[item.skill]} · Target {item.target}</p>
                  <p className="mt-1 text-sm text-muted">{item.comparison}</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink">{item.tips.map((tip) => <li key={tip}>{tip}</li>)}</ul>
                  <Link className="btn-primary mt-3 inline-flex" to={item.destination}>Take {labels[item.skill]} again</Link>
                </div>
              ))}
            </div>
          </Card>
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          {progress.skills.map((skill) => {
            const value = skill.accuracy_percent ?? (skill.estimate_high ? skill.estimate_high / 12 * 100 : 0)
            const summary = skill.accuracy_percent !== null ? `${skill.accuracy_percent}% practice accuracy` : skill.estimate_low !== null ? `Estimated ${skill.estimate_low}–${skill.estimate_high}` : 'No completed attempts yet'
            return <Card key={skill.skill} className="p-5"><div className="flex items-center justify-between"><h2 className="text-xl font-bold text-ink">{labels[skill.skill]}</h2><span className="text-sm font-semibold text-muted">Target {skill.target}</span></div><p className="mt-2 text-2xl font-bold text-brand">{summary}</p><div className="mt-3"><Meter value={value} label={`${labels[skill.skill]}: ${summary}`} /></div><p className="mt-2 text-sm text-muted">{skill.attempts} completed attempt{skill.attempts === 1 ? '' : 's'}</p></Card>
          })}
        </div>
        <Card className="p-5"><h2 className="flex items-center gap-2 text-xl font-bold text-ink"><ShieldCheck className="text-good" size={21} /> Overall readiness</h2><p className="mt-2 text-sm leading-6 text-muted">{progress.readiness_explanation}</p><p className="mt-2 text-xs font-semibold text-muted">Coverage: {progress.coverage.practised_skills} of 4 skills · {progress.disclaimer}</p></Card>
        <section><h2 className="flex items-center gap-2 text-2xl font-bold text-ink"><BarChart3 size={23} /> Attempt history</h2>{progress.trends.length ? <div className="mt-3 overflow-x-auto rounded-card border border-line"><table className="w-full text-left text-sm"><thead className="bg-surface-secondary text-muted"><tr><th className="p-3">Date</th><th className="p-3">Skill</th><th className="p-3">Measure</th><th className="p-3">Value</th></tr></thead><tbody>{[...progress.trends].reverse().map((trend, index) => <tr key={`${trend.date}-${index}`} className="border-t border-line"><td className="p-3 tabular-nums">{new Date(trend.date).toLocaleDateString()}</td><td className="p-3 font-semibold">{labels[trend.skill]}</td><td className="p-3 text-muted">{trend.label}</td><td className="p-3 font-bold text-brand">{trend.metric === 'accuracy_percent' ? `${trend.value}%` : trend.value}</td></tr>)}</tbody></table></div> : <EmptyAction />}</section>
        {progress.task_types.length > 0 && <section><h2 className="flex items-center gap-2 text-2xl font-bold text-ink"><Target size={23} /> Task-type accuracy</h2><div className="mt-3 grid gap-3 md:grid-cols-2">{progress.task_types.map((task) => <Card key={task.task_type} className="p-4"><div className="flex justify-between gap-3"><h3 className="font-bold text-ink">{task.title}</h3><span className="font-bold text-brand">{task.accuracy_percent}%</span></div><p className="mt-1 text-xs text-muted">{task.correct} of {task.total} correct</p></Card>)}</div></section>}
      </>}
    </div>
  )
}

function EmptyAction() { return <Card className="mt-3 p-5 text-sm text-muted">No submitted attempts yet. <Link className="font-bold text-brand" to="/practice">Start focused practice</Link>.</Card> }
function AccountRequired({ title }: { title: string }) { return <Card className="mx-auto max-w-xl text-center"><h1 className="text-3xl font-bold text-ink">{title}</h1><p className="mt-3 text-muted">Create a loose account or sign in to keep private progress across devices.</p><div className="mt-5 flex justify-center gap-3"><Link className="btn-primary" to="/register">Create account</Link><Link className="btn-secondary" to="/signin">Sign in</Link></div></Card> }
export { AccountRequired }
