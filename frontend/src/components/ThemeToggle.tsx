import { Monitor, Moon, Sun } from 'lucide-react'
import { themeOrder, useTheme } from '../app/theme'

const icons = { system: Monitor, light: Sun, dark: Moon } as const

/** Cycles light → dark → system, matching the reference app's affordance. */
export function ThemeToggle() {
  const { theme, cycleTheme } = useTheme()
  const Icon = icons[theme]
  const nextTheme = themeOrder[(themeOrder.indexOf(theme) + 1) % themeOrder.length]

  return (
    <button
      onClick={cycleTheme}
      className="flex h-11 w-11 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface-secondary hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
      aria-label={`${theme} theme. Switch to ${nextTheme} theme.`}
      title={`Switch to ${nextTheme} theme`}
    >
      <Icon size={21} />
    </button>
  )
}
