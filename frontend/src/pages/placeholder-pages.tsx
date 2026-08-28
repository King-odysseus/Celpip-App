import { PlaceholderPage } from './PlaceholderPage'

export function LearnPage() {
  return (
    <PlaceholderPage
      eyebrow="Understand the test"
      title="Learn"
      description="Task-type guides, strategy, timing, original examples, and common mistakes for each of the four skills."
    />
  )
}

export function PracticePage() {
  return (
    <PlaceholderPage
      eyebrow="Targeted practice"
      title="Practice"
      description="Choose a skill, task type, and difficulty, then work through an exercise player at your own pace."
    />
  )
}

export function MockPage() {
  return (
    <PlaceholderPage
      eyebrow="Full simulation"
      title="Mock Tests"
      description="Start or resume realistic Listening → Reading → Writing → Speaking sessions with server-timed sections and delayed results."
    />
  )
}

export function MistakesPage() {
  return (
    <PlaceholderPage
      eyebrow="Learn from errors"
      title="Mistake Bank"
      description="Filter repeated patterns, work a review queue, and track which mistakes you have resolved."
    />
  )
}

export function ProgressPage() {
  return (
    <PlaceholderPage
      eyebrow="Track your trends"
      title="Progress"
      description="Four independent skill trends, task-type accuracy, practice volume, and the history of your practice estimates."
    />
  )
}

export function StudyPlanPage() {
  return (
    <PlaceholderPage
      eyebrow="Stay on schedule"
      title="Study Plan"
      description="Your preferences, a daily calendar of tasks, completion tracking, and adaptations based on how your practice is going."
    />
  )
}

export function NotFoundPage() {
  return (
    <PlaceholderPage
      eyebrow="Error 404"
      title="Page not found"
      description="The page you were looking for does not exist. Use the navigation to return to a known destination."
    />
  )
}
