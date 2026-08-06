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
      className={`flex items-start gap-2.5 rounded-md border border-[#e5cfcd] bg-[#faf0ef] px-3.5 py-2.5 text-[13px] leading-relaxed text-error ${className}`}
    >
      <svg
        width="15"
        height="15"
        viewBox="0 0 16 16"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        className="mt-[3px] shrink-0"
        aria-hidden="true"
      >
        <circle cx="8" cy="8" r="6" />
        <path d="M8 5v3.5M8 11h.01" />
      </svg>
      <span>{message}</span>
    </div>
  )
}
