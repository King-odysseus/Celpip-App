import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from './AppShell'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { AccountPage } from '../features/auth/AccountPage'
import { ProtectedRoute } from '../features/auth/ProtectedRoute'
import { RegisterPage } from '../features/auth/RegisterPage'
import { SignInPage } from '../features/auth/SignInPage'
import { RecoveryPage } from '../features/auth/RecoveryPage'
import { ReadingCatalogPage } from '../features/reading/ReadingCatalogPage'
import { ReadingSessionPage } from '../features/reading/ReadingSessionPage'
import {
  MistakesPage,
  MockPage,
  NotFoundPage,
  ProgressPage,
  StudyPlanPage,
} from '../pages/placeholder-pages'

/**
 * All destinations nested inside the shell. Sample pages (Learn, Practice, …)
 * and the Dashboard stay public; only the Account route requires a session.
 */
export const routes = [
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'learn', element: <ReadingCatalogPage mode="learn" /> },
      { path: 'practice', element: <ReadingCatalogPage mode="practice" /> },
      { path: 'reading/session/:sessionId', element: <ReadingSessionPage /> },
      { path: 'mock', element: <MockPage /> },
      { path: 'mistakes', element: <MistakesPage /> },
      { path: 'progress', element: <ProgressPage /> },
      { path: 'study-plan', element: <StudyPlanPage /> },
      { path: 'register', element: <RegisterPage /> },
      { path: 'signin', element: <SignInPage /> },
      { path: 'recovery', element: <RecoveryPage /> },
      {
        path: 'account',
        element: (
          <ProtectedRoute>
            <AccountPage />
          </ProtectedRoute>
        ),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
