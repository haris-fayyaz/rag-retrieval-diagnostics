import type { RetrievedChunk as Chunk } from '../api/client'
import Disclosure from './Disclosure'

export function RetrievedChunk({ chunk, position }: { chunk: Chunk; position: number }) {
  return (
    <article className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[11px] text-muted-foreground">Chunk {position}</span>
        <span className="text-[#d4d4d4]">·</span>
        <span className="text-[12.5px] font-medium text-foreground">{chunk.document_name}</span>
        <span className="ml-auto font-mono text-[11px] text-subtle-foreground">
          Score {chunk.score.toFixed(2)}
        </span>
      </div>
      <p className="border-l border-border pl-3 text-[13px] leading-relaxed text-subtle-foreground">
        {chunk.text}
      </p>
    </article>
  )
}

export default function RetrievedContext({ chunks }: { chunks: Chunk[] }) {
  if (chunks.length === 0) return null

  return (
    <Disclosure
      label="Retrieved context"
      meta={`${chunks.length} ${chunks.length === 1 ? 'chunk' : 'chunks'}`}
    >
      <div className="flex flex-col divide-y divide-border">
        {chunks.map((chunk, i) => (
          <div key={`${chunk.document_id}-${i}`} className="py-3.5 first:pt-0 last:pb-0">
            <RetrievedChunk chunk={chunk} position={i + 1} />
          </div>
        ))}
      </div>
    </Disclosure>
  )
}
