import { AlertIcon } from './icons'

/** Reusable, user-safe error surface. Never renders server internals. */
export default function ErrorMessage({
  message,
  className = '',
}: {
  message: string
  className?: string
}) {
  return (
    <div
      role="alert"
      className={`animate-fade-in flex items-start gap-2.5 rounded-md border border-border-strong bg-secondary px-3.5 py-2.5 text-[13px] leading-relaxed text-foreground ${className}`}
    >
      <AlertIcon width={15} height={15} className="mt-[3px] shrink-0 text-foreground" />
      <span>{message}</span>
    </div>
  )
}