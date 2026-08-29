import { render } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '../app/theme'
import { AuthProvider } from '../features/auth/AuthProvider'
import { routes } from '../app/router'

/**
 * Render the real application (shell + routes) at a given path using an
 * in-memory router, so navigation, theming, and auth behave as in production.
 * The test setup stubs `fetch`, so the auth bootstrap resolves to anonymous.
 *
 * Pass `initialState` to seed the first location's history state, and use the
 * returned `router` to drive or inspect navigation (e.g. for one-shot route
 * state).
 */
export function renderApp(initialPath = '/', options?: { state?: unknown }) {
  const initialEntry =
    options?.state !== undefined
      ? { pathname: initialPath, state: options.state }
      : initialPath
  const router = createMemoryRouter(routes, {
    initialEntries: [initialEntry],
  })
  const view = render(
    <ThemeProvider>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </ThemeProvider>,
  )
  return { ...view, router }
}
