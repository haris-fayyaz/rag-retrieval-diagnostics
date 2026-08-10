import { useEffect, useRef, useState } from 'react'
import { ApiError, api, type AnswerResponse, type Document } from '../api/client'
import AssistantMessage, { AssistantBody } from '../components/AssistantMessage'
import ChatHeader from '../components/ChatHeader'
import CitationList from '../components/CitationList'
import DiagnosticDetails from '../components/DiagnosticDetails'
import EmptyState from '../components/EmptyState'
import ErrorMessage from '../components/ErrorMessage'
import LoadingState, { type LoadingPhase } from '../components/LoadingState'
import MessageComposer from '../components/MessageComposer'
import RetrievedContext from '../components/RetrievedContext'
import StatusBadge from '../components/StatusBadge'
import UserMessage from '../components/UserMessage'

type Turn =
  | { kind: 'question'; id: string; text: string }
  | { kind: 'answer'; id: string; response: AnswerResponse }
  | { kind: 'error'; id: string; message: string }

const SUGGESTIONS = [
  'Summarize this document',
  'Find information about...',
  'Explain a concept from my sources',
]

export default function AnswerPage({
  documents,
  selectedIds,
  onToggleSource,
  topK,
  onTopKChange,
  retrievalMode,
  onRetrievalModeChange,
  pipelineMode,
  onPipelineModeChange,
  turns,
  onTurnsChange,
  onManageDocuments,
  onOpenNav,
}: {
  documents: Document[]
  selectedIds: string[]
  onToggleSource: (id: string) => void
  topK: number
  onTopKChange: (topK: number) => void
  retrievalMode: string
  onRetrievalModeChange: (mode: string) => void
  pipelineMode: string
  onPipelineModeChange: (mode: string) => void
  turns: Turn[]
  onTurnsChange: (turns: Turn[]) => void
  onManageDocuments: () => void
  onOpenNav: () => void
}) {
  const [draft, setDraft] = useState('')
  const [phase, setPhase] = useState<LoadingPhase | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [turns, phase])

  async function ask() {
    const question = draft.trim()
    if (!question || phase) return

    const next: Turn[] = [...turns, { kind: 'question', id: `q-${Date.now()}`, text: question }]
    onTurnsChange(next)
    setDraft('')
    setPhase('retrieving')

    const toGenerating = setTimeout(() => setPhase('generating'), 700)

    try {
      const response = await api.answer({
        question,
        document_ids: selectedIds,
        top_k: topK,
        retrieval_mode: retrievalMode,
        pipeline_mode: pipelineMode,
      })
      onTurnsChange([...next, { kind: 'answer', id: response.request_id, response }])
    } catch (err) {
      onTurnsChange([
        ...next,
        {
          kind: 'error',
          id: `e-${Date.now()}`,
          message: err instanceof ApiError ? err.message : 'Something went wrong. Please try again.',
        },
      ])
    } finally {
      clearTimeout(toGenerating)
      setPhase(null)
    }
  }

  const isEmpty = turns.length === 0 && !phase

  return (
    <div className="flex h-full min-w-0 flex-col">
      <ChatHeader
        title="RAG Assistant"
        subtitle="Grounded answers from your selected sources"
        onMenuClick={onOpenNav}
      />

      {isEmpty ? (
        <div className="flex min-h-0 flex-1 flex-col justify-center">
          <div className="mx-auto w-full max-w-[860px] px-5 md:px-8">
            <EmptyState
              title="How can I help?"
              description="Ask a question using the documents you provide as context."
              suggestions={SUGGESTIONS}
              onSuggestionClick={setDraft}
            />
            <div className="mt-10">
              <MessageComposer
                value={draft}
                onChange={setDraft}
                onSubmit={ask}
                documents={documents}
                selectedIds={selectedIds}
                topK={topK}
                retrievalMode={retrievalMode}
                onRetrievalModeChange={onRetrievalModeChange}
                pipelineMode={pipelineMode}
                onPipelineModeChange={onPipelineModeChange}
                onToggleSource={onToggleSource}
                onTopKChange={onTopKChange}
                onManageDocuments={onManageDocuments}
              />
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="scroll-quiet min-h-0 flex-1 overflow-y-auto">
            <div className="mx-auto flex w-full max-w-[860px] flex-col gap-8 px-5 py-8 md:px-8">
              {turns.map((turn) => {
                if (turn.kind === 'question') return <UserMessage key={turn.id} text={turn.text} />

                if (turn.kind === 'error')
                  return (
                    <AssistantMessage key={turn.id}>
                      <ErrorMessage message={turn.message} />
                    </AssistantMessage>
                  )

                const { response } = turn
                return (
                  <AssistantMessage
                    key={turn.id}
                    footer={
                      <>
                        {response.has_context ? (
                          <CitationList citations={response.citations} />
                        ) : (
                          <div>
                            <StatusBadge tone="warning" dot>
                              No relevant context
                            </StatusBadge>
                          </div>
                        )}
                        <div className="flex flex-col gap-2">
                          <RetrievedContext chunks={response.chunks} />
                          <DiagnosticDetails
                            retrievalMs={response.retrieval_ms}
                            generationMs={response.generation_ms}
                            requestId={response.request_id}
                            extra={[
                              ...(response.retrieval_mode ? [{ label: 'Retrieval mode', value: response.retrieval_mode }] : []),
                              ...(response.provider ? [{ label: 'Provider', value: response.provider }] : []),
                            ]}
                          />
                        </div>
                      </>
                    }
                  >
                    {response.has_context ? (
                      <AssistantBody text={response.answer} />
                    ) : (
                      <div className="rounded-md border border-[#e6dcc4] bg-[#fbf8f1] px-4 py-3 text-[14.5px] leading-relaxed text-subtle-foreground">
                        {response.answer}
                      </div>
                    )}
                  </AssistantMessage>
                )
              })}

              {phase && <LoadingState phase={phase} />}
              <div ref={bottomRef} />
            </div>
          </div>

          <div className="shrink-0 border-t border-border bg-background px-5 pb-5 pt-4 md:px-8">
            <div className="mx-auto w-full max-w-[860px]">
              <MessageComposer
                value={draft}
                onChange={setDraft}
                onSubmit={ask}
                disabled={phase !== null}
                documents={documents}
                selectedIds={selectedIds}
                topK={topK}
                retrievalMode={retrievalMode}
                onRetrievalModeChange={onRetrievalModeChange}
                pipelineMode={pipelineMode}
                onPipelineModeChange={onPipelineModeChange}
                onToggleSource={onToggleSource}
                onTopKChange={onTopKChange}
                onManageDocuments={onManageDocuments}
              />
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export type { Turn }