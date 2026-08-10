import { useEffect, useRef } from 'react'
import type { Document } from '../api/client'
import Button from './Button'
import { CheckIcon, DocumentIcon, PlusIcon } from './icons'

export function SourceButton({
  count,
  open,
  onClick,
}: {
  count: number
  open: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      aria-expanded={open}
      aria-label="Add sources"
      className={`flex h-9 shrink-0 items-center gap-1.5 rounded-md border pl-2 pr-2 text-[13px] font-medium transition-colors duration-150 ${
        count > 0
          ? 'border-[#d8dbd1] bg-accent-surface text-accent'
          : open
            ? 'border-[#d0d0d0] bg-secondary text-foreground'
            : 'border-border bg-background text-subtle-foreground hover:border-[#d0d0d0] hover:bg-secondary hover:text-foreground'
      }`}
    >
      <PlusIcon className={`transition-transform duration-200 ${open ? 'rotate-45' : ''}`} />
      {count > 0 && <span className="pr-0.5 font-mono text-[12px]">{count}</span>}
    </button>
  )
}

export default function SourceSelector({
  documents,
  selectedIds,
  topK,
  retrievalMode,
  pipelineMode,
  onToggle,
  onTopKChange,
  onRetrievalModeChange,
  onPipelineModeChange,
  onClose,
  onManageDocuments,
}: {
  documents: Document[]
  selectedIds: string[]
  topK: number
  retrievalMode: string
  pipelineMode: string
  onToggle: (id: string) => void
  onTopKChange: (topK: number) => void
  onRetrievalModeChange: (mode: string) => void
  onPipelineModeChange: (mode: string) => void
  onClose: () => void
  onManageDocuments: () => void
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      if (!ref.current?.contains(event.target as Node)) onClose()
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [onClose])

  return (
    <div
      ref={ref}
      role="dialog"
      aria-label="Add sources"
      className="animate-scale-in absolute bottom-[calc(100%+10px)] left-0 z-20 w-[336px] origin-bottom-left overflow-hidden rounded-lg border border-border bg-background shadow-[0_12px_28px_-18px_rgba(0,0,0,0.28)]"
    >
      <div className="flex items-baseline justify-between border-b border-border px-4 py-3">
        <h3 className="text-[13.5px] font-semibold">Add sources</h3>
        <span className="font-mono text-[11px] text-muted-foreground">
          {selectedIds.length}/{documents.length}
        </span>
      </div>

      <p className="label-caps px-4 pt-3">Select documents</p>

      <div className="scroll-quiet max-h-[212px] overflow-y-auto px-2 py-2">
        {documents.length === 0 ? (
          <p className="px-2 py-4 text-[13px] leading-relaxed text-muted-foreground">
            No documents yet. Add one from the Documents screen to use it as a source.
          </p>
        ) : (
          documents.map((doc) => {
            const checked = selectedIds.includes(doc.id)
            return (
              <button
                key={doc.id}
                onClick={() => onToggle(doc.id)}
                aria-pressed={checked}
                className={`flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left transition-colors duration-150 ${
                  checked ? 'bg-accent-surface' : 'hover:bg-secondary'
                }`}
              >
                <span
                  className={`flex h-[17px] w-[17px] shrink-0 items-center justify-center rounded-[4px] border ${
                    checked ? 'border-accent bg-accent text-accent-foreground' : 'border-[#cfcfcf] bg-background'
                  }`}
                >
                  {checked && <CheckIcon width={11} height={11} strokeWidth={2} />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13.5px] font-medium text-foreground">
                    {doc.name}
                  </span>
                  <span className="block truncate font-mono text-[11px] text-muted-foreground">
                    {doc.id} · {doc.chunk_count} chunks
                  </span>
                </span>
              </button>
            )
          })
        )}
      </div>

      <div className="flex flex-col gap-3 border-t border-border px-4 py-3">
        <div className="grid grid-cols-2 gap-x-3 gap-y-2.5">
          <label className="flex items-center gap-2 text-[12.5px] text-muted-foreground">
            Top K
            <input
              type="number"
              min={1}
              max={20}
              value={topK}
              onChange={(e) => onTopKChange(Math.min(20, Math.max(1, Number(e.target.value) || 1)))}
              className="h-7 w-14 rounded-sm border border-border bg-background px-2 text-center font-mono text-[12px] text-foreground focus:border-accent focus:outline-none"
            />
          </label>
          <label className="flex items-center gap-2 text-[12.5px] text-muted-foreground">
            Retrieval
            <select
              value={retrievalMode}
              onChange={(e) => onRetrievalModeChange(e.target.value)}
              className="h-7 rounded-sm border border-border bg-background px-1.5 text-[12px] text-foreground focus:border-accent focus:outline-none"
            >
              <option value="tfidf">tfidf</option>
              <option value="semantic">semantic</option>
              <option value="hybrid">hybrid</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-[12.5px] text-muted-foreground">
            Pipeline
            <select
              value={pipelineMode}
              onChange={(e) => onPipelineModeChange(e.target.value)}
              className="h-7 rounded-sm border border-border bg-background px-1.5 text-[12px] text-foreground focus:border-accent focus:outline-none"
            >
              <option value="custom">custom</option>
              <option value="langchain">langchain</option>
            </select>
          </label>
        </div>
        <Button size="sm" onClick={onClose}>
          Done
        </Button>
      </div>

      <button
        onClick={onManageDocuments}
        className="flex w-full items-center gap-2 border-t border-border bg-muted px-4 py-2.5 text-[12.5px] text-subtle-foreground transition-colors hover:text-foreground"
      >
        <DocumentIcon width={14} height={14} />
        Manage documents
      </button>
    </div>
  )
}
