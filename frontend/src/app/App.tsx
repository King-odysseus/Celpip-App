import { RouterProvider } from 'react-router-dom'
import { ThemeProvider } from './theme'
import { AuthProvider } from '../features/auth/AuthProvider'
import { router } from './router'

export function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </ThemeProvider>
  )
}
