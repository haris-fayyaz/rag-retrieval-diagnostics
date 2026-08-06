import { AppMark } from './icons'

export type LoadingPhase = 'retrieving' | 'generating'

const copy: Record<LoadingPhase, string> = {
  retrieving: 'Searching sources...',
  generating: 'Generating answer...',
}

export default function LoadingState({ phase }: { phase: LoadingPhase }) {
  return (
    <div className="flex gap-3.5">
      <span className="mt-[2px] shrink-0 text-primary">
        <AppMark />
      </span>
      <div className="flex-1">
        <p className="mb-2 text-[12px] font-medium tracking-[0.02em] text-muted-foreground">
          RAG Assistant
        </p>
        <p className="flex items-center gap-2.5 text-[14px] text-subtle-foreground" aria-live="polite">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-70" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
          </span>
          {copy[phase]}
        </p>
      </div>
    </div>
  )
}
