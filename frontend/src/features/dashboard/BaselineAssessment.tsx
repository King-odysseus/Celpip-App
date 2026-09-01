import { ArrowRight, BookOpen, CheckCircle2, Headphones, Mic, PenLine } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, CardTitle } from '../../components/ui'
import type { Dashboard, Skill } from '../learning/types'
import { SKILL_LABELS } from './labels'

const SKILL_ICONS: Record<Skill, typeof BookOpen> = {
  listening: Headphones,
  reading: BookOpen,
  writing: PenLine,
  speaking: Mic,
}

function pathFor(skill: Skill): string {
  return skill === 'reading' ? '/practice' : `/practice/${skill}`
}

/** Gives new learners a simple, visible route to collect their first evidence. */
export function BaselineAssessment({ skills }: { skills: Dashboard['skills'] }) {
  const completed = skills.filter((item) => item.attempts > 0).length
  if (completed === skills.length) return null

  return (
    <Card className="border-accent/30 bg-accent-soft/20">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div className="min-w-0">
          <p className="eyebrow">Build your baseline</p>
          <CardTitle className="mt-1">See where to focus first</CardTitle>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
            Complete one short activity in each skill. Your dashboard will then compare your practice evidence with your target and recommend what to work on next.
          </p>
        </div>
        <span className="rounded-full bg-surface px-3 py-1.5 text-xs font-bold tabular-nums text-brand">
          {completed}/4 skills started
        </span>
      </div>

      <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {skills.map((skill) => {
          const Icon = SKILL_ICONS[skill.skill]
          const started = skill.attempts > 0
          return (
            <Link
              key={skill.skill}
              to={pathFor(skill.skill)}
              className={`flex min-h-14 items-center gap-3 rounded-input border px-3 py-2.5 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${started ? 'border-good/30 bg-good-soft/60' : 'border-line bg-surface hover:border-brand/40 hover:bg-brand-soft/30'}`}
            >
              {started ? <CheckCircle2 size={19} className="shrink-0 text-good" aria-hidden /> : <Icon size={19} className="shrink-0 text-accent" aria-hidden />}
              <span className="min-w-0 flex-1 text-sm font-semibold text-ink">{SKILL_LABELS[skill.skill]}</span>
              {!started && <ArrowRight size={16} className="shrink-0 text-muted" aria-hidden />}
            </Link>
          )
        })}
      </div>

      <Link to="/diagnostic" className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-brand hover:underline">
        Open baseline assessment <ArrowRight size={16} aria-hidden="true" />
      </Link>
    </Card>
  )
}
