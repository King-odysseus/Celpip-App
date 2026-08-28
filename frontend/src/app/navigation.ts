import {
  BarChart3,
  BookOpen,
  CalendarRange,
  ClipboardList,
  LayoutDashboard,
  ListChecks,
  Timer,
  type LucideIcon,
} from 'lucide-react'

export type NavItem = {
  to: string
  label: string
  /** Shorter label for the compact mobile bar. */
  mobileLabel?: string
  icon: LucideIcon
  end?: boolean
}

/**
 * The seven primary destinations, in the order shown in the desktop header.
 * Mirrors the information architecture in the platform plan.
 */
export const primaryNav: NavItem[] = [
  { to: '/', label: 'Dashboard', mobileLabel: 'Home', icon: LayoutDashboard, end: true },
  { to: '/learn', label: 'Learn', icon: BookOpen },
  { to: '/practice', label: 'Practice', icon: ClipboardList },
  { to: '/mock', label: 'Mock Tests', mobileLabel: 'Mock', icon: Timer },
  { to: '/mistakes', label: 'Mistake Bank', mobileLabel: 'Mistakes', icon: ListChecks },
  { to: '/progress', label: 'Progress', icon: BarChart3 },
  { to: '/study-plan', label: 'Study Plan', mobileLabel: 'Plan', icon: CalendarRange },
]

/**
 * Mobile bottom bar shows four primary items plus a More overflow — never
 * seven crowded tabs. More surfaces the remaining destinations.
 */
export const mobilePrimaryPaths = ['/', '/practice', '/mock', '/progress']

export const mobilePrimaryNav: NavItem[] = mobilePrimaryPaths.map(
  (path) => primaryNav.find((item) => item.to === path)!,
)

/** Destinations reachable from the mobile "More" sheet. */
export const mobileOverflowNav: NavItem[] = primaryNav.filter(
  (item) => !mobilePrimaryPaths.includes(item.to),
)
