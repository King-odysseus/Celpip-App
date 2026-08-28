import { type ReactNode } from 'react'
import { Card } from '../../components/ui'

/** Centered, single-column layout shared by the auth pages. */
export function AuthLayout({
  eyebrow,
  title,
  description,
  children,
  footer,
}: {
  eyebrow: string
  title: string
  description: string
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <section aria-labelledby="auth-title" className="mx-auto max-w-md space-y-5">
      <header className="space-y-1.5 text-center">
        <p className="eyebrow">{eyebrow}</p>
        <h1
          id="auth-title"
          className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl"
        >
          {title}
        </h1>
        <p className="text-sm text-muted">{description}</p>
      </header>
      <Card>{children}</Card>
      {footer && <div className="text-center text-sm text-muted">{footer}</div>}
    </section>
  )
}

/** Accessible inline error banner for form-level failures. */
export function FormError({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <p
      role="alert"
      className="rounded-xl border border-bad/40 bg-bad-soft px-3 py-2 text-sm text-bad"
    >
      {message}
    </p>
  )
}
