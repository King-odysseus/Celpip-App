import type { StudyPlan } from './types'

/** Lesson slugs completed across plan versions and submitted practice. */
export function completedLessonSlugs(plan: StudyPlan): Set<string> {
  const slugs = new Set<string>(plan.completed_lessons ?? [])
  for (const task of plan.tasks) {
    if (task.state !== 'completed' && !task.previously_completed) continue
    try {
      const lesson = new URL(task.destination, window.location.origin).searchParams.get('lesson')
      if (lesson) slugs.add(lesson)
    } catch {
      // Ignore a malformed legacy destination; the plan remains usable.
    }
  }
  return slugs
}
