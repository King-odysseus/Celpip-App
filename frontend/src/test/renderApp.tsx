import { render } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '../app/theme'
import { AuthProvider } from '../features/auth/AuthProvider'
import { routes } from '../app/router'

/**
 * Render the real application (shell + routes) at a given path using an
 * in-memory router, so navigation, theming, and auth behave as in production.
 * The test setup stubs `fetch`, so the auth bootstrap resolves to anonymous.
 */
export function renderApp(initialPath = '/') {
  const router = createMemoryRouter(routes, {
    initialEntries: [initialPath],
  })
  return render(
    <ThemeProvider>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </ThemeProvider>,
  )
}
