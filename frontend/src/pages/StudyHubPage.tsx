import { ArrowRight, BookOpen, CalendarRange, Headphones, Mic2, PenLine } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card } from '../components/ui'

const studyLinks = [
  { to: '/learn', title: 'Reading', description: 'Build comprehension with guided passages and task strategies.', icon: BookOpen },
  { to: '/learn/listening', title: 'Listening', description: 'Study conversations, announcements, and viewpoints with feedback.', icon: Headphones },
  { to: '/learn/writing', title: 'Writing', description: 'Learn how to structure emails and survey responses.', icon: PenLine },
  { to: '/learn/speaking', title: 'Speaking', description: 'Plan responses and practise each speaking task type.', icon: Mic2 },
  { to: '/study-plan', title: 'Study plan', description: 'Follow a schedule shaped around your target and recent activity.', icon: CalendarRange },
]

export function StudyHubPage() {
  return (
    <div className="mx-auto w-full max-w-[1600px] space-y-8 animate-fade-up">
      <header className="rounded-card bg-brand px-5 py-8 text-white shadow-elevated sm:px-8">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent-soft">Build confidence first</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Study</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-white/80 sm:text-base">
          Learn the task, see a reliable strategy, and prepare before moving into timed practice.
        </p>
      </header>
      <section aria-labelledby="study-options-title">
        <h2 id="study-options-title" className="text-2xl font-bold text-ink">Choose a skill</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {studyLinks.map(({ to, title, description, icon: Icon }) => (
            <Link key={to} to={to} className="group">
              <Card className="h-full p-5 transition group-hover:-translate-y-0.5 group-hover:shadow-card-hover">
                <Icon className="text-accent" size={24} />
                <h3 className="mt-4 text-xl font-bold text-ink">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
                <span className="mt-5 inline-flex items-center gap-1 text-sm font-bold text-brand">Open <ArrowRight size={16} /></span>
              </Card>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
