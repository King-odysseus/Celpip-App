import { lazy, Suspense, type ReactNode } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from './AppShell'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { AccountPage } from '../features/auth/AccountPage'
import { ProtectedRoute } from '../features/auth/ProtectedRoute'
import { RegisterPage } from '../features/auth/RegisterPage'
import { SignInPage } from '../features/auth/SignInPage'
import { RecoveryPage } from '../features/auth/RecoveryPage'
import { ReadingSessionPage } from '../features/reading/ReadingSessionPage'
import { WritingSessionPage } from '../features/writing/WritingSessionPage'
import { SpeakingSessionPage } from '../features/speaking/SpeakingSessionPage'
import { ProgressPage } from '../features/learning/ProgressPage'
import { NotFoundPage } from '../pages/placeholder-pages'
import { StudyHubPage } from '../pages/StudyHubPage'
import { ReviewHubPage } from '../pages/ReviewHubPage'
import { DiagnosticPage } from '../features/dashboard/DiagnosticPage'

const ReadingCatalogPage = lazy(() => import('../features/reading/ReadingCatalogPage').then((module) => ({ default: module.ReadingCatalogPage })))
const WritingCatalogPage = lazy(() => import('../features/writing/WritingCatalogPage').then((module) => ({ default: module.WritingCatalogPage })))
const SpeakingCatalogPage = lazy(() => import('../features/speaking/SpeakingCatalogPage').then((module) => ({ default: module.SpeakingCatalogPage })))
const MockTestsPage = lazy(() => import('../features/mocks/MockTestsPage').then((module) => ({ default: module.MockTestsPage })))
const MockWorkspacePage = lazy(() => import('../features/mocks/MockWorkspacePage').then((module) => ({ default: module.MockWorkspacePage })))
const MistakesPage = lazy(() => import('../features/learning/MistakesPage').then((module) => ({ default: module.MistakesPage })))
const StudyPlanPage = lazy(() => import('../features/learning/StudyPlanPage').then((module) => ({ default: module.StudyPlanPage })))

function RouteLoading() {
  return <p role="status" className="py-16 text-center text-muted">Loading practice workspace…</p>
}

function LazyRoute({ children }: { children: ReactNode }) {
  return <Suspense fallback={<RouteLoading />}>{children}</Suspense>
}

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
      { path: 'learn', element: <LazyRoute><ReadingCatalogPage mode="learn" /></LazyRoute> },
      { path: 'learn/listening', element: <LazyRoute><ReadingCatalogPage mode="learn" skill="listening" /></LazyRoute> },
      { path: 'learn/writing', element: <LazyRoute><WritingCatalogPage mode="learn" /></LazyRoute> },
      { path: 'learn/speaking', element: <LazyRoute><SpeakingCatalogPage mode="learn" /></LazyRoute> },
      { path: 'practice', element: <LazyRoute><ReadingCatalogPage mode="practice" /></LazyRoute> },
      { path: 'practice/listening', element: <LazyRoute><ReadingCatalogPage mode="practice" skill="listening" /></LazyRoute> },
      { path: 'practice/writing', element: <LazyRoute><WritingCatalogPage mode="practice" /></LazyRoute> },
      { path: 'practice/speaking', element: <LazyRoute><SpeakingCatalogPage mode="practice" /></LazyRoute> },
      { path: 'reading/session/:sessionId', element: <ReadingSessionPage /> },
      { path: 'writing/session/:sessionId', element: <WritingSessionPage /> },
      { path: 'speaking/session/:sessionId', element: <SpeakingSessionPage /> },
      { path: 'mock', element: <LazyRoute><MockTestsPage /></LazyRoute> },
      { path: 'mock/:attemptId', element: <LazyRoute><MockWorkspacePage /></LazyRoute> },
      { path: 'mistakes', element: <LazyRoute><MistakesPage /></LazyRoute> },
      { path: 'progress', element: <ProgressPage /> },
      { path: 'study-plan', element: <LazyRoute><StudyPlanPage /></LazyRoute> },
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
