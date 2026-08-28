import { type HTMLAttributes, type ReactNode } from 'react'

export function Card({
  className = '',
  children,
  ...props
}: HTMLAttributes<HTMLDivElement> & { children: ReactNode }) {
  return (
    <div className={`card p-4 sm:p-5 ${className}`} {...props}>
      {children}
    </div>
  )
}

export function CardTitle({
  className = '',
  children,
}: {
  className?: string
  children: ReactNode
}) {
  return (
    <h2 className={`text-lg font-semibold tracking-tight text-ink ${className}`}>
      {children}
    </h2>
  )
}
