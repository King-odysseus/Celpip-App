import { type ReactNode } from 'react'
import { Card } from '../components/ui'

/**
 * Honest empty-state scaffold used by every Phase 1A destination. Each page
 * states what it will become without implying a feature already exists.
 */
export function PlaceholderPage({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string
  title: string
  description: string
  children?: ReactNode
}) {
  return (
    <section aria-labelledby="page-title" className="space-y-5">
      <header className="space-y-1.5">
        <p className="eyebrow">{eyebrow}</p>
        <h1 id="page-title" className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
          {title}
        </h1>
        <p className="max-w-2xl text-sm text-muted sm:text-base">{description}</p>
      </header>

      <Card>
        <p className="text-sm text-muted">
          This area is part of the Phase 1A shell. The feature it will hold has
          not been built yet.
        </p>
      </Card>

      {children}
    </section>
  )
}
