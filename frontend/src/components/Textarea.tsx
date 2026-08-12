import type { TextareaHTMLAttributes } from 'react'

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  hint?: string
}

export default function Textarea({ label, hint, id, className = '', ...props }: TextareaProps) {
  return (
    <div className="flex flex-col gap-2">
      {label && (
        <label htmlFor={id} className="label-caps">
          {label}
        </label>
      )}
      <textarea
        id={id}
        {...props}
        className={`w-full resize-y rounded-md border border-border bg-background px-3 py-2.5 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground transition-colors duration-150 hover:border-[#d0d0d0] focus:border-foreground focus:outline-none focus:ring-1 focus:ring-foreground/15 ${className}`}
      />
      {hint && <p className="text-[12px] text-muted-foreground">{hint}</p>}
    </div>
  )
}
