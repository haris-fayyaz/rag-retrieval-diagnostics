import type { Citation as CitationType } from '../api/client'

export function Citation({ citation, index }: { citation: CitationType; index: number }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-sm border border-border bg-background py-[3px] pl-[3px] pr-2.5 text-[12.5px] transition-colors hover:border-[#d0d0d0]">
      <span className="flex h-4 w-4 items-center justify-center rounded-[3px] bg-secondary font-mono text-[10px] text-subtle-foreground">
        {index}
      </span>
      <span className="font-medium text-foreground">{citation.document_name}</span>
      <span className="text-[#c4c4c4]">·</span>
      <span className="text-muted-foreground">Chunk {citation.chunk_index}</span>
    </span>
  )
}

export default function CitationList({ citations }: { citations: CitationType[] }) {
  if (citations.length === 0) return null

  return (
    <div className="flex flex-col gap-2">
      <p className="label-caps">Sources</p>
      <div className="flex flex-wrap gap-1.5">
        {citations.map((citation, i) => (
          <Citation key={`${citation.document_id}-${citation.chunk_index}`} citation={citation} index={i + 1} />
        ))}
      </div>
    </div>
  )
}
