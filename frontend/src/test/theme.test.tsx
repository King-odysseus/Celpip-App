import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderApp } from './renderApp'

describe('ThemeToggle', () => {
  it('starts in system mode with no data-theme override', () => {
    renderApp()
    expect(document.documentElement.hasAttribute('data-theme')).toBe(false)
    // There is a header toggle and (potentially) a hidden mobile one; grab the
    // first with a system-mode label.
    expect(
      screen.getAllByRole('button', { name: /system theme/i })[0],
    ).toBeInTheDocument()
  })

  it('cycles light → dark → system and persists the choice', async () => {
    const user = userEvent.setup()
    renderApp()
    const toggle = () =>
      screen.getAllByRole('button', { name: /switch to .* theme/i })[0]

    // system → light
    await user.click(toggle())
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    expect(localStorage.getItem('celpip-theme')).toBe('light')

    // light → dark
    await user.click(toggle())
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')

    // dark → system (override removed)
    await user.click(toggle())
    expect(document.documentElement.hasAttribute('data-theme')).toBe(false)
    expect(localStorage.getItem('celpip-theme')).toBe('system')
  })

  it('restores a persisted theme on load', () => {
    localStorage.setItem('celpip-theme', 'dark')
    renderApp()
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })
})
