import type { Skill } from './types'

/**
 * What separates a strong-but-average response from a top-band one, per
 * skill. This is deliberately generic across every task in a skill — the
 * per-task-type strategy/common_mistakes (TaskTypeGuides) already covers
 * task-specific steps, so this section covers the standard that applies no
 * matter which task comes up: completeness, precision, organization, and
 * range. Original guidance; not CELPIP's own scoring rubric.
 */
export type LevelTwelveGuide = {
  skill: Skill
  headline: string
  /** The one habit that most separates a 9–10 response from an 11–12. */
  keyShift: string
  checklist: string[]
}

export const LEVEL_TWELVE_GUIDANCE: Record<Skill, LevelTwelveGuide> = {
  listening: {
    skill: 'listening',
    headline: 'Separate what was said from what you inferred',
    keyShift:
      'A mid-band answer picks the option that sounds familiar. A top-band answer can point to the exact line of the recording that supports it — and reject options that are only partly true.',
    checklist: [
      'Before the audio starts, read every question stem and prediction what each one is really asking (a fact, an opinion, a reason, or a sequence).',
      'Take notes in short fragments, not full sentences — you only have time to capture keywords, numbers, and who said what.',
      'When two speakers disagree or a plan changes mid-conversation, note the final decision separately from the earlier ideas that were rejected.',
      'Distinguish a stated fact from your own reasonable guess — both can be correct, but treat them differently when checking an answer.',
      'If you are unsure between two choices, pick the one every part of which is supported by the recording, not just most of it.',
      'Never leave a question blank — an educated guess after elimination beats a guaranteed zero.',
    ],
  },
  reading: {
    skill: 'reading',
    headline: 'Answer the question that was asked, not the one that looks similar',
    keyShift:
      'A mid-band answer matches a true detail from the passage. A top-band answer matches the exact scope of the question — main idea versus supporting detail, stated claim versus implication.',
    checklist: [
      'Skim structure first (headings, opening/closing lines, table rows and columns) before reading any question closely.',
      'Underline or note the specific sentence that answers each question — if you cannot point to it, you have not found the answer yet.',
      'Watch for exceptions and conditions ("unless", "except", "only if") — they are often the difference between two similar-looking choices.',
      'Do not choose an option just because it is a true statement from the passage; it must also answer the specific question.',
      'For vocabulary-in-context questions, test your choice by re-reading the sentence with your word substituted in — it should keep the same meaning and tone.',
      'Manage time so no single passage consumes time you need for the others; skip and return rather than stall.',
    ],
  },
  writing: {
    skill: 'writing',
    headline: 'Complete the task fully, in an organized, appropriately toned response',
    keyShift:
      'A mid-band response is grammatically fine but generic or incomplete. A top-band response addresses every part of the prompt directly, in a clear structure, with vocabulary and tone matched to the reader.',
    checklist: [
      'Before writing, list every sub-task in the prompt (e.g. explain a problem, request an action, propose a date) and make sure your draft answers each one.',
      'Open and close with the tone the situation calls for — formal for an official request, warm for a personal message — and hold that tone throughout.',
      'Organize into clear paragraphs: a purpose statement, supporting detail or reasoning, and a closing action or request. Avoid a single wall of text.',
      'Use precise, varied vocabulary and sentence structure rather than repeating the same simple sentence pattern throughout.',
      'Stay inside the target word range — too short usually means an underdeveloped idea; too long risks losing focus and time.',
      'Reserve the last few minutes to reread for agreement, tense consistency, and any missing sub-task before time runs out.',
    ],
  },
  speaking: {
    skill: 'speaking',
    headline: 'Use the full response time with a clear structure, not just correct grammar',
    keyShift:
      'A mid-band response is understandable but thin or hesitant. A top-band response is fluent, organized, and fully developed for the entire response window, with natural connectors and appropriate detail.',
    checklist: [
      'During preparation time, jot two or three key points and a rough order — do not try to script full sentences you cannot finish.',
      'Start with a direct opening sentence that states your point, scene, or story before adding detail — do not warm up for several seconds first.',
      'Use connecting language ("because", "as a result", "for example", "on the other hand") to link ideas instead of listing disconnected sentences.',
      'For image-based tasks, work through the scene systematically (foreground to background, or left to right) so nothing important is skipped.',
      'Keep speaking for the entire response window; running out of things to say well before time is up is a stronger signal than a small grammar slip.',
      'Recover naturally from a mistake — briefly self-correct and continue, rather than stopping or restarting the whole response.',
    ],
  },
}
