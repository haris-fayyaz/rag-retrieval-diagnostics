import type { ReactNode } from 'react'
import { AppMark } from './icons'

/** Minimal inline formatter: **bold** and `code`. */
function formatInline(text: string, keyPrefix: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean)
  return parts.map((part, i) => {
    const key = `${keyPrefix}-${i}`
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={key} className="font-semibold text-foreground">
          {part.slice(2, -2)}
        </strong>
      )
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code
          key={key}
          className="rounded-[4px] border border-border bg-secondary px-1 py-[1px] font-mono text-[12.5px] text-foreground"
        >
          {part.slice(1, -1)}
        </code>
      )
    }
    return <span key={key}>{part}</span>
  })
}

/** Renders paragraphs, unordered lists and fenced code blocks. */
export function AssistantBody({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  const segments = text.split(/```/)

  segments.forEach((segment, si) => {
    if (si % 2 === 1) {
      const [maybeLang, ...rest] = segment.replace(/^\n/, '').split('\n')
      const hasLang = /^[a-z]+$/i.test(maybeLang.trim()) && rest.length > 0
      const code = (hasLang ? rest.join('\n') : segment.trim()).replace(/\n$/, '')
      blocks.push(
        <pre
          key={`code-${si}`}
          className="scroll-quiet overflow-x-auto rounded-md border border-border bg-muted px-4 py-3 font-mono text-[12.5px] leading-relaxed text-foreground"
        >
          <code>{code}</code>
        </pre>,
      )
      return
    }

    segment
      .split(/\n{2,}/)
      .map((b) => b.trim())
      .filter(Boolean)
      .forEach((block, bi) => {
        const key = `b-${si}-${bi}`
        const lines = block.split('\n')
        if (lines.every((l) => /^[-*]\s+/.test(l.trim()))) {
          blocks.push(
            <ul key={key} className="flex flex-col gap-1.5 pl-1">
              {lines.map((line, li) => (
                <li key={li} className="flex gap-2.5">
                  <span className="mt-[10px] h-[3px] w-[3px] shrink-0 rounded-full bg-[#b0b0b0]" />
                  <span>{formatInline(line.replace(/^[-*]\s+/, ''), `${key}-${li}`)}</span>
                </li>
              ))}
            </ul>,
          )
          return
        }
        blocks.push(
          <p key={key} className="text-pretty">
            {formatInline(block, key)}
          </p>,
        )
      })
  })

  return (
    <div className="flex flex-col gap-4 text-[15px] leading-[1.72] text-foreground">{blocks}</div>
  )
}

export default function AssistantMessage({
  children,
  footer,
}: {
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="flex gap-3.5">
      <span className="mt-[2px] shrink-0 text-primary">
        <AppMark />
      </span>
      <div className="min-w-0 flex-1">
        <p className="mb-2 text-[12px] font-medium tracking-[0.02em] text-muted-foreground">
          RAG Assistant
        </p>
        {children}
        {footer && <div className="mt-5 flex flex-col gap-3">{footer}</div>}
      </div>
    </div>
  )
}
