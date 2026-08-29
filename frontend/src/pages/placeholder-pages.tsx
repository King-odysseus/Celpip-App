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

export function NotFoundPage() {
  return (
    <PlaceholderPage
      eyebrow="Error 404"
      title="Page not found"
      description="The page you were looking for does not exist. Use the navigation to return to a known destination."
    />
  )
}
