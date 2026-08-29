import {
  type ButtonHTMLAttributes,
  type ReactNode,
  type Ref,
} from 'react'
import { Link } from 'react-router-dom'

export type ButtonVariant = 'primary' | 'accent' | 'secondary' | 'ghost' | 'danger'

const variants: Record<ButtonVariant, string> = {
  primary: 'button-neomorphic bg-brand text-white hover:opacity-90',
  accent: 'button-neomorphic bg-accent-fill text-white hover:bg-accent-fill-hover',
  secondary: 'bg-surface text-ink border border-line hover:border-brand',
  ghost: 'text-muted hover:text-ink hover:bg-surface-secondary',
  danger: 'button-neomorphic bg-bad text-white hover:opacity-90',
}

// Pill shape for major actions; min height keeps a 44px touch target.
const base =
  'inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-4 py-2.5 ' +
  'text-sm font-medium transition active:scale-[0.98] ' +
  'disabled:opacity-40 disabled:cursor-not-allowed ' +
  'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand'

export function Button({
  variant = 'primary',
  className = '',
  ref,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  ref?: Ref<HTMLButtonElement>
}) {
  return (
    <button
      ref={ref}
      className={`${base} ${variants[variant]} ${className}`}
      {...props}
    />
  )
}

export function ButtonLink({
  to,
  variant = 'primary',
  className = '',
  children,
}: {
  to: string
  variant?: ButtonVariant
  className?: string
  children: ReactNode
}) {
  return (
    <Link to={to} className={`${base} ${variants[variant]} ${className}`}>
      {children}
    </Link>
  )
}
