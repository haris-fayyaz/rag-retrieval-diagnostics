import type { ReactNode } from 'react'
import { DotsIcon } from './icons'

export default function ChatHeader({
  title,
  subtitle,
  onMenuClick,
  aside,
}: {
  title: string
  subtitle: string
  /** Rendered on small screens to reveal the sidebar. */
  onMenuClick?: () => void
  aside?: ReactNode
}) {
  return (
    <header className="flex h-16 shrink-0 items-center gap-3 border-b border-border bg-background/85 px-5 backdrop-blur-sm md:px-8">
      {onMenuClick && (
        <button
          onClick={onMenuClick}
          aria-label="Open navigation"
          className="-ml-1 flex h-9 w-9 items-center justify-center rounded-md text-subtle-foreground transition-colors hover:bg-secondary md:hidden"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round">
            <path d="M2.5 4.5h11M2.5 8h11M2.5 11.5h11" />
          </svg>
        </button>
      )}

      <div className="min-w-0 flex-1">
        <h1 className="truncate text-[15px] font-semibold tracking-[-0.01em]">{title}</h1>
        <p className="truncate text-[12.5px] text-muted-foreground">{subtitle}</p>
      </div>

      {aside}

      <button
        aria-label="Options"
        className="flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
      >
        <DotsIcon />
      </button>
    </header>
  )
}
