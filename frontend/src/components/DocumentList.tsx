import type { Document } from '../api/client'
import { DocumentIcon } from './icons'

export function DocumentItem({ document }: { document: Document }) {
  return (
    <li className="flex items-center gap-3.5 px-4 py-3.5 transition-colors hover:bg-muted">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border bg-background text-[#9a9a9a]">
        <DocumentIcon />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[14px] font-medium text-foreground">{document.name}</p>
        <p className="truncate font-mono text-[11.5px] text-muted-foreground">{document.id}</p>
      </div>
      <span className="shrink-0 font-mono text-[12px] text-subtle-foreground">
        {document.chunk_count} chunks
      </span>
    </li>
  )
}

export default function DocumentList({
  documents,
  loading,
}: {
  documents: Document[]
  loading: boolean
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <div className="flex items-baseline justify-between border-b border-border bg-muted px-4 py-2.5">
        <h2 className="text-[13.5px] font-semibold">Documents</h2>
        <span className="font-mono text-[11.5px] text-muted-foreground">
          {loading ? '—' : documents.length}
        </span>
      </div>

      {loading ? (
        <p className="px-4 py-6 text-[13px] text-muted-foreground">Loading documents...</p>
      ) : documents.length === 0 ? (
        <p className="px-4 py-6 text-[13px] leading-relaxed text-muted-foreground">
          No documents yet. Add one above to make it available as a source in chat.
        </p>
      ) : (
        <ul className="divide-y divide-border">
          {documents.map((doc) => (
            <DocumentItem key={doc.id} document={doc} />
          ))}
        </ul>
      )}
    </div>
  )
}
