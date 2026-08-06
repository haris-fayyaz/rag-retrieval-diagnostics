import type { ReactNode } from 'react'

type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'error'

const tones: Record<Tone, string> = {
  neutral: 'border-border bg-secondary text-subtle-foreground',
  accent: 'border-[#d8dbd1] bg-accent-surface text-accent',
  success: 'border-[#cfdacf] bg-[#f1f5f0] text-success',
  warning: 'border-[#e6dcc4] bg-[#f8f4ea] text-warning',
  error: 'border-[#e5cfcd] bg-[#faf0ef] text-error',
}

export default function StatusBadge({
  tone = 'neutral',
  dot = false,
  children,
}: {
  tone?: Tone
  dot?: boolean
  children: ReactNode
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-sm border px-2 py-[3px] text-[11px] font-medium tracking-[0.02em] ${tones[tone]}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  )
}
