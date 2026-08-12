import { useEffect, useRef, useState } from 'react'
import type { Document } from '../api/client'
import SourceSelector, { SourceButton } from './SourceSelector'
import { ArrowUpIcon, CloseIcon } from './icons'

export default function MessageComposer({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = 'Ask anything about your selected sources...',
  documents,
  selectedIds,
  topK,
  retrievalMode,
  pipelineMode,
  onToggleSource,
  onTopKChange,
  onRetrievalModeChange,
  onPipelineModeChange,
  onManageDocuments,
}: {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  disabled?: boolean
  placeholder?: string
  documents: Document[]
  selectedIds: string[]
  topK: number
  retrievalMode: string
  pipelineMode: string
  onToggleSource: (id: string) => void
  onTopKChange: (topK: number) => void
  onRetrievalModeChange: (mode: string) => void
  onPipelineModeChange: (mode: string) => void
  onManageDocuments: () => void
}) {
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Grow with content up to a fixed ceiling, then scroll.
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 168)}px`
  }, [value])

  const selectedDocs = documents.filter((d) => selectedIds.includes(d.id))
  const canSend = value.trim().length > 0 && !disabled

  return (
    <div className="relative">
      {sourcesOpen && (
        <SourceSelector
          documents={documents}
          selectedIds={selectedIds}
          topK={topK}
          retrievalMode={retrievalMode}
          pipelineMode={pipelineMode}
          onToggle={onToggleSource}
          onTopKChange={onTopKChange}
          onRetrievalModeChange={onRetrievalModeChange}
          onPipelineModeChange={onPipelineModeChange}
          onClose={() => setSourcesOpen(false)}
          onManageDocuments={() => {
            setSourcesOpen(false)
            onManageDocuments()
          }}
        />
      )}

      <div className="rounded-xl border border-border bg-background shadow-[0_2px_10px_-6px_rgba(0,0,0,0.18)] transition-colors duration-150 focus-within:border-[#c9c9c9]">
        {selectedDocs.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 border-b border-border px-3 py-2.5">
            <span className="label-caps pr-0.5">Sources</span>
            {selectedDocs.map((doc) => (
              <span
                key={doc.id}
                className="inline-flex items-center gap-1.5 rounded-sm border border-emphasis-border bg-emphasis-surface py-[2px] pl-2 pr-1 text-[12px] font-medium text-foreground"
              >
                {doc.name}
                <button
                  onClick={() => onToggleSource(doc.id)}
                  aria-label={`Remove ${doc.name}`}
                  className="flex h-4 w-4 items-center justify-center rounded-[3px] transition-colors hover:bg-[#e0e0e0]"
                >
                  <CloseIcon width={9} height={9} strokeWidth={1.8} />
                </button>
              </span>
            ))}
          </div>
        )}

        <div className="flex items-end gap-2 p-2.5">
          <SourceButton
            count={selectedIds.length}
            open={sourcesOpen}
            onClick={() => setSourcesOpen((v) => !v)}
          />

          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            disabled={disabled}
            placeholder={placeholder}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                if (canSend) onSubmit()
              }
            }}
            className="scroll-quiet max-h-[168px] min-h-[36px] flex-1 resize-none border-0 bg-transparent px-1 py-[7px] text-[15px] leading-[1.5] text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-60"
          />

          <button
            onClick={onSubmit}
            disabled={!canSend}
            aria-label="Send message"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground transition-all duration-150 hover:bg-[#262626] disabled:bg-[#e0e0e0] disabled:text-[#a8a8a8] lg:h-9 lg:w-9"
          >
            <ArrowUpIcon strokeWidth={1.6} />
          </button>
        </div>
      </div>

      <p className="mt-2 px-1 text-center text-[11.5px] text-muted-foreground">
        Answers are grounded in the selected sources. Retrieval depth{' '}
        <span className="font-mono">top_k {topK}</span>.
      </p>
    </div>
  )
}
