import type { ReactNode } from 'react'
import { AlertIcon, CheckIcon } from './icons'

/** Two grayscale weights instead of hue-per-meaning: 'solid' reads as the
 *  emphasized/important state, 'neutral' as informational/secondary. */
type Tone = 'neutral' | 'solid'
type Icon = 'check' | 'alert' | 'none'

const tones: Record<Tone, string> = {
  neutral: 'border-border bg-secondary text-subtle-foreground',
  solid: 'border-foreground bg-foreground text-background',
}

const icons: Record<Exclude<Icon, 'none'>, typeof CheckIcon> = {
  check: CheckIcon,
  alert: AlertIcon,
}

export default function StatusBadge({
  tone = 'neutral',
  icon = 'none',
  dot = false,
  children,
}: {
  tone?: Tone
  /** Preferred over `dot` when the state has a clear meaning to convey. */
  icon?: Icon
  dot?: boolean
  children: ReactNode
}) {
  const Icon = icon !== 'none' ? icons[icon] : null

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-sm border px-2 py-[3px] text-[11px] font-medium tracking-[0.02em] ${tones[tone]}`}
    >
      {Icon && <Icon width={11} height={11} strokeWidth={1.8} />}
      {dot && !Icon && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  )
}
