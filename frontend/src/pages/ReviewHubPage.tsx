import { ArrowRight, BarChart3, ListChecks } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card } from '../components/ui'

const reviewLinks = [
  { to: '/mistakes', title: 'Review mistakes', description: 'Turn repeated errors into focused follow-up practice.', icon: ListChecks },
  { to: '/progress', title: 'My progress', description: 'See accuracy, activity, and skill-by-skill signals.', icon: BarChart3 },
]

export function ReviewHubPage() {
  return (
    <div className="mx-auto w-full max-w-[1600px] space-y-8 animate-fade-up">
      <header>
        <p className="eyebrow">Learn from every attempt</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-ink sm:text-4xl">Review</h1>
        <p className="mt-3 max-w-2xl text-muted">Use your results to decide what to practise next.</p>
      </header>
      <div className="grid gap-4 sm:grid-cols-2">
        {reviewLinks.map(({ to, title, description, icon: Icon }) => (
          <Link key={to} to={to} className="group">
            <Card className="h-full p-6 transition group-hover:-translate-y-0.5 group-hover:shadow-card-hover">
              <Icon className="text-accent" size={26} />
              <h2 className="mt-4 text-xl font-bold text-ink">{title}</h2>
              <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
              <span className="mt-5 inline-flex items-center gap-1 text-sm font-bold text-brand">Open <ArrowRight size={16} /></span>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}
