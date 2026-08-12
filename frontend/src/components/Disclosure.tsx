import { useState, type ReactNode } from 'react'
import { ChevronIcon } from './icons'

/** Compact expandable row used for retrieved context and diagnostics so the
 *  technical layer never dominates the conversation. */
export default function Disclosure({
  label,
  meta,
  children,
  defaultOpen = false,
}: {
  label: string
  meta?: string
  children: ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="rounded-md border border-border bg-background">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex h-9 w-full items-center gap-2 px-3 text-left text-[12.5px] font-medium text-subtle-foreground transition-colors hover:text-foreground"
      >
        <ChevronIcon
          className={`shrink-0 text-[#9a9a9a] transition-transform duration-200 ${open ? '' : '-rotate-90'}`}
        />
        <span>{label}</span>
        {meta && (
          <>
            <span className="text-[#c4c4c4]">·</span>
            <span className="font-normal text-muted-foreground">{meta}</span>
          </>
        )}
      </button>
      {open && <div className="animate-slide-up border-t border-border px-3.5 py-3.5">{children}</div>}
    </div>
  )
}
