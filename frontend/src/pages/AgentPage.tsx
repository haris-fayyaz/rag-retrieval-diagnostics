import { useState, type FormEvent } from 'react'
import { ApiError, api, type AgentResponse } from '../api/client'
import AssistantMessage, { AssistantBody } from '../components/AssistantMessage'
import Button from '../components/Button'
import ChatHeader from '../components/ChatHeader'
import CitationList from '../components/CitationList'
import DiagnosticDetails from '../components/DiagnosticDetails'
import ErrorMessage from '../components/ErrorMessage'
import StatusBadge from '../components/StatusBadge'
import Textarea from '../components/Textarea'
import UserMessage from '../components/UserMessage'

const STATUS_TONE: Record<AgentResponse['status'], 'success' | 'warning' | 'error'> = {
  success: 'success',
  no_context: 'warning',
  refused: 'warning',
  tool_error: 'error',
}

export default function AgentPage({ onOpenNav }: { onOpenNav: () => void }) {
  const [question, setQuestion] = useState('')
  const [asked, setAsked] = useState<string | null>(null)
  const [result, setResult] = useState<AgentResponse | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const text = question.trim()
    if (!text || running) return

    setRunning(true)
    setError(null)
    setResult(null)
    setAsked(text)
    try {
      setResult(await api.agentQuery(text))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="flex h-full min-w-0 flex-col">
      <ChatHeader
        title="Agent query"
        subtitle="The assistant selects a tool and answers in a single run"
        onMenuClick={onOpenNav}
        aside={
          <div className="hidden sm:block">
            <StatusBadge tone="accent">/agent/query</StatusBadge>
          </div>
        }
      />

      <div className="scroll-quiet min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-[860px] flex-col gap-8 px-5 py-8 md:px-8">
          <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
            <Textarea
              id="agent-question"
              label="Question"
              placeholder="Ask the agent..."
              rows={3}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
            <div>
              <Button type="submit" disabled={running || !question.trim()}>
                {running ? 'Running agent...' : 'Run agent'}
              </Button>
            </div>
          </form>

          {error && <ErrorMessage message={error} />}

          {asked && (
            <div className="flex flex-col gap-8 border-t border-border pt-8">
              <UserMessage text={asked} />

              {running ? (
                <p className="flex items-center gap-2.5 pl-[34px] text-[14px] text-subtle-foreground">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-70" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
                  </span>
                  Running agent...
                </p>
              ) : (
                result && (
                  <AssistantMessage
                    footer={
                      <>
                        <div className="flex flex-wrap items-center gap-1.5">
                          <StatusBadge tone={STATUS_TONE[result.status]} dot>
                            {result.status}
                          </StatusBadge>
                          <StatusBadge tone="accent">Tool · {result.tool}</StatusBadge>
                          <StatusBadge>
                            {result.steps} {result.steps === 1 ? 'step' : 'steps'}
                          </StatusBadge>
                        </div>
                        <CitationList citations={result.citations} />
                        <DiagnosticDetails
                          requestId={result.request_id}
                          extra={[
                            { label: 'Selected tool', value: result.tool },
                            { label: 'Steps', value: String(result.steps) },
                            { label: 'Status', value: result.status },
                          ]}
                        />
                      </>
                    }
                  >
                    <AssistantBody text={result.answer} />
                  </AssistantMessage>
                )
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}