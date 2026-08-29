/**
 * Local, optimistic word count for live feedback. It mirrors the server's
 * authoritative count (`len(text.split())` in Python: split on any run of
 * whitespace, ignoring leading/trailing whitespace). The submitted count shown
 * in the review always comes from the server.
 */
export function countWords(text: string): number {
  const trimmed = text.trim()
  if (!trimmed) return 0
  return trimmed.split(/\s+/).length
}

export type TargetState = 'below' | 'within' | 'above'

export function targetState(count: number, min: number, max: number): TargetState {
  if (count < min) return 'below'
  if (count > max) return 'above'
  return 'within'
}
