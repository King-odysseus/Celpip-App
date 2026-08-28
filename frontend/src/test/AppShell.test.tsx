import { describe, expect, it } from 'vitest'
import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderApp } from './renderApp'
import { primaryNav } from '../app/navigation'

describe('AppShell', () => {
  it('renders the brand and a skip-to-content link', () => {
    renderApp()
    expect(screen.getByText('CELPIP Practice')).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /skip to main content/i }),
    ).toBeInTheDocument()
  })

  it('exposes all seven primary destinations in the desktop nav', () => {
    renderApp()
    const nav = screen.getByRole('navigation', { name: 'Primary' })
    for (const item of primaryNav) {
      expect(
        within(nav).getByRole('link', { name: item.label }),
      ).toBeInTheDocument()
    }
  })

  it('marks the current destination as active', () => {
    renderApp('/practice')
    const nav = screen.getByRole('navigation', { name: 'Primary' })
    const active = within(nav).getByRole('link', { name: 'Practice' })
    expect(active).toHaveClass('bg-brand-soft')
  })

  it('renders the mobile bar with four primary items plus More', () => {
    renderApp()
    const mobileNav = screen.getByRole('navigation', { name: 'Primary mobile' })
    // Home, Practice, Mock, Progress links + the More button = 5 controls.
    expect(within(mobileNav).getAllByRole('link')).toHaveLength(4)
    expect(within(mobileNav).getByRole('button', { name: 'More' })).toBeInTheDocument()
  })
})

describe('routing', () => {
  it('renders each placeholder destination heading', async () => {
    const cases: Array<[string, string]> = [
      ['/', 'Dashboard'],
      ['/learn', 'Learn'],
      ['/practice', 'Practice'],
      ['/mock', 'Mock Tests'],
      ['/mistakes', 'Mistake Bank'],
      ['/progress', 'Progress'],
      ['/study-plan', 'Study Plan'],
    ]
    for (const [path, heading] of cases) {
      const { unmount } = renderApp(path)
      expect(
        screen.getByRole('heading', { level: 1, name: heading }),
      ).toBeInTheDocument()
      unmount()
    }
  })

  it('shows a 404 page for unknown routes', () => {
    renderApp('/does-not-exist')
    expect(
      screen.getByRole('heading', { level: 1, name: /page not found/i }),
    ).toBeInTheDocument()
  })
})

describe('mobile More overflow', () => {
  it('opens a dialog exposing the overflow destinations', async () => {
    const user = userEvent.setup()
    renderApp()
    await user.click(screen.getByRole('button', { name: 'More' }))
    const dialog = screen.getByRole('dialog', { name: /more destinations/i })
    expect(within(dialog).getByRole('link', { name: 'Learn' })).toBeInTheDocument()
    expect(
      within(dialog).getByRole('link', { name: 'Mistake Bank' }),
    ).toBeInTheDocument()
    expect(
      within(dialog).getByRole('link', { name: 'Study Plan' }),
    ).toBeInTheDocument()
  })

  it('closes the overflow dialog with Escape', async () => {
    const user = userEvent.setup()
    renderApp()
    const trigger = screen.getByRole('button', { name: 'More' })
    await user.click(trigger)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })

  it('traps keyboard focus inside the overflow dialog', async () => {
    const user = userEvent.setup()
    renderApp()
    await user.click(screen.getByRole('button', { name: 'More' }))
    const dialog = screen.getByRole('dialog')
    const close = within(dialog).getByRole('button', { name: 'Close menu' })
    expect(close).toHaveFocus()

    await user.tab({ shift: true })
    expect(dialog).toContainElement(document.activeElement as HTMLElement)

    const focusable = dialog.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
    )
    focusable[focusable.length - 1].focus()
    await user.tab()
    expect(close).toHaveFocus()
  })
})
