import {
  BookOpen,
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
  { to: '/study', label: 'Study', icon: BookOpen },
  { to: '/practice', label: 'Practice', icon: ClipboardList },
  { to: '/mock', label: 'Mock Test', mobileLabel: 'Mock', icon: Timer },
  { to: '/review', label: 'Review', icon: ListChecks },
]

/**
 * Mobile bottom bar shows four primary items plus a More overflow — never
 * seven crowded tabs. More surfaces the remaining destinations.
 */
export const mobilePrimaryPaths = ['/', '/practice', '/mock', '/review']

export const mobilePrimaryNav: NavItem[] = mobilePrimaryPaths.map(
  (path) => primaryNav.find((item) => item.to === path)!,
)

/** Destinations reachable from the mobile "More" sheet. */
export const mobileOverflowNav: NavItem[] = primaryNav.filter(
  (item) => !mobilePrimaryPaths.includes(item.to),
)
