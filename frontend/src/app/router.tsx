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
import { WritingCatalogPage } from '../features/writing/WritingCatalogPage'
import { WritingSessionPage } from '../features/writing/WritingSessionPage'
import { SpeakingCatalogPage } from '../features/speaking/SpeakingCatalogPage'
import { SpeakingSessionPage } from '../features/speaking/SpeakingSessionPage'
import { MockTestsPage } from '../features/mocks/MockTestsPage'
import { MockWorkspacePage } from '../features/mocks/MockWorkspacePage'
import { NotFoundPage } from '../pages/placeholder-pages'
import { MistakesPage } from '../features/learning/MistakesPage'
import { ProgressPage } from '../features/learning/ProgressPage'
import { StudyPlanPage } from '../features/learning/StudyPlanPage'
import { StudyHubPage } from '../pages/StudyHubPage'
import { ReviewHubPage } from '../pages/ReviewHubPage'
import { DiagnosticPage } from '../features/dashboard/DiagnosticPage'

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
      { path: 'diagnostic', element: <DiagnosticPage /> },
      { path: 'study', element: <StudyHubPage /> },
      { path: 'learn', element: <ReadingCatalogPage mode="learn" /> },
      { path: 'learn/listening', element: <ReadingCatalogPage mode="learn" skill="listening" /> },
      { path: 'learn/writing', element: <WritingCatalogPage mode="learn" /> },
      { path: 'learn/speaking', element: <SpeakingCatalogPage mode="learn" /> },
      { path: 'practice', element: <ReadingCatalogPage mode="practice" /> },
      { path: 'practice/listening', element: <ReadingCatalogPage mode="practice" skill="listening" /> },
      { path: 'practice/writing', element: <WritingCatalogPage mode="practice" /> },
      { path: 'practice/speaking', element: <SpeakingCatalogPage mode="practice" /> },
      { path: 'reading/session/:sessionId', element: <ReadingSessionPage /> },
      { path: 'writing/session/:sessionId', element: <WritingSessionPage /> },
      { path: 'speaking/session/:sessionId', element: <SpeakingSessionPage /> },
      { path: 'mock', element: <MockTestsPage /> },
      { path: 'mock/:attemptId', element: <MockWorkspacePage /> },
      { path: 'mistakes', element: <MistakesPage /> },
      { path: 'progress', element: <ProgressPage /> },
      { path: 'study-plan', element: <StudyPlanPage /> },
      { path: 'review', element: <ReviewHubPage /> },
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
