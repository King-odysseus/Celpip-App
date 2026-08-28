import { useId, type InputHTMLAttributes } from 'react'

export function Field({
  label,
  hint,
  className = '',
  id,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const hintId = hint ? `${inputId}-hint` : undefined

  return (
    <div className="block">
      <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium text-ink">
        {label}
      </label>
      <input
        id={inputId}
        aria-describedby={hintId}
        className={`min-h-11 w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-ink
          focus-visible:border-brand focus-visible:outline-2 focus-visible:outline-offset-1
          focus-visible:outline-brand ${className}`}
        {...props}
      />
      {hint && (
        <span id={hintId} className="mt-1.5 block text-xs text-muted">
          {hint}
        </span>
      )}
    </div>
  )
}
