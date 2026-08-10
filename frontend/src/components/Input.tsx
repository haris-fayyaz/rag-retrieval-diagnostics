import type { InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  hint?: string
}

export default function Input({ label, hint, id, className = '', ...props }: InputProps) {
  return (
    <div className="flex flex-col gap-2">
      {label && (
        <label htmlFor={id} className="label-caps">
          {label}
        </label>
      )}
      <input
        id={id}
        {...props}
        className={`h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground transition-colors duration-150 hover:border-[#d0d0d0] focus:border-foreground focus:outline-none focus:ring-1 focus:ring-foreground/15 ${className}`}
      />
      {hint && <p className="text-[12px] text-muted-foreground">{hint}</p>}
    </div>
  )
}
