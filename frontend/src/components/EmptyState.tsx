export default function EmptyState({
  title,
  description,
  suggestions = [],
  onSuggestionClick,
}: {
  title: string
  description: string
  suggestions?: string[]
  onSuggestionClick?: (suggestion: string) => void
}) {
  return (
    <div className="flex flex-col items-center px-6 text-center">
      <h2 className="text-[26px] font-semibold tracking-[-0.02em] text-foreground">{title}</h2>
      <p className="mt-2.5 max-w-[420px] text-[14px] leading-relaxed text-muted-foreground">
        {description}
      </p>

      {suggestions.length > 0 && (
        <div className="mt-8 flex flex-wrap justify-center gap-2">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => onSuggestionClick?.(suggestion)}
              className="rounded-md border border-border bg-background px-3.5 py-2 text-[13px] text-subtle-foreground transition-colors duration-150 hover:border-[#d0d0d0] hover:bg-secondary hover:text-foreground"
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
