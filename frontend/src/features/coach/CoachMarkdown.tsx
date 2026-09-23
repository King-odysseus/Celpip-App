import { Fragment, type ReactNode } from 'react'

// Lightweight renderer for the subset of markdown the coach returns:
// paragraphs, bullet/numbered lists, **bold** and *italic*.
function renderInline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*)/g).map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={index} className="font-semibold">{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
      return <em key={index}>{part.slice(1, -1)}</em>
    }
    return <Fragment key={index}>{part}</Fragment>
  })
}

export function CoachMarkdown({ content }: { content: string }) {
  const blocks = content.trim().split(/\n{2,}/)

  return (
    <div className="space-y-2.5 break-words [overflow-wrap:anywhere]">
      {blocks.map((block, blockIndex) => {
        const lines = block.split('\n').filter((line) => line.trim())
        const bullet = /^\s*[-*•]\s+/
        const numbered = /^\s*\d+[.)]\s+/

        if (lines.length > 0 && lines.every((line) => bullet.test(line))) {
          return (
            <ul key={blockIndex} className="list-disc space-y-1 pl-5 marker:text-brand">
              {lines.map((line, i) => <li key={i}>{renderInline(line.replace(bullet, ''))}</li>)}
            </ul>
          )
        }
        if (lines.length > 0 && lines.every((line) => numbered.test(line))) {
          return (
            <ol key={blockIndex} className="list-decimal space-y-1 pl-5 marker:font-semibold marker:text-brand">
              {lines.map((line, i) => <li key={i}>{renderInline(line.replace(numbered, ''))}</li>)}
            </ol>
          )
        }
        return (
          <p key={blockIndex}>
            {lines.map((line, i) => (
              <Fragment key={i}>
                {i > 0 && <br />}
                {renderInline(line.replace(/^#{1,6}\s+/, ''))}
              </Fragment>
            ))}
          </p>
        )
      })}
    </div>
  )
}
