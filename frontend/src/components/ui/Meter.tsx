import { useEffect, useRef, useState } from 'react'

/** Horizontal progress/mastery bar. Announces its value to assistive tech. */
export function Meter({
  value,
  max = 100,
  label,
}: {
  value: number
  max?: number
  label?: string
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  const tone = pct >= 75 ? 'bg-good' : pct >= 50 ? 'bg-warn' : 'bg-bad'
  const [width, setWidth] = useState(0)
  const mounted = useRef(false)

  useEffect(() => {
    // Grow from zero on first paint, then ease between value changes. The
    // reduced-motion CSS rule collapses the transition duration for users who
    // ask for less motion.
    if (!mounted.current) {
      mounted.current = true
      const id = requestAnimationFrame(() => setWidth(pct))
      return () => cancelAnimationFrame(id)
    }
    setWidth(pct)
  }, [pct])

  return (
    <div
      role="meter"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
      className="h-2 w-full overflow-hidden rounded-full bg-line"
    >
      <div
        className={`h-full rounded-full ${tone} transition-[width] duration-700 ease-out`}
        style={{ width: `${width}%` }}
      />
    </div>
  )
}
