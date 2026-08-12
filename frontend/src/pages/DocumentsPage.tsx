import { useState, type FormEvent } from 'react'
import { ApiError, api, type Document } from '../api/client'
import Button from '../components/Button'
import ChatHeader from '../components/ChatHeader'
import DocumentList from '../components/DocumentList'
import ErrorMessage from '../components/ErrorMessage'
import Input from '../components/Input'
import Textarea from '../components/Textarea'
import { CheckIcon } from '../components/icons'

export default function DocumentsPage({
  documents,
  loading,
  onRefresh,
  onOpenNav,
}: {
  documents: Document[]
  loading: boolean
  onRefresh: () => Promise<void>
  onOpenNav: () => void
}) {
  const [name, setName] = useState('')
  const [text, setText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [created, setCreated] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    setCreated(null)
    try {
      const doc = await api.createDocument(name.trim(), text)
      await onRefresh()
      setName('')
      setText('')
      setCreated(`Added “${doc.name}” · ${doc.chunk_count} chunks`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex h-full min-w-0 flex-col">
      <ChatHeader
        title="Documents"
        subtitle="Text you add here becomes available as a source in chat"
        onMenuClick={onOpenNav}
      />

      <div className="scroll-quiet min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-[860px] flex-col gap-9 px-5 py-8 md:px-8">
          <section className="flex flex-col gap-4">
            <div>
              <h2 className="text-[16px] font-semibold tracking-[-0.01em]">Add document</h2>
              <p className="mt-1 text-[13px] text-muted-foreground">
                Documents are chunked and indexed on creation.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <Input
                id="doc-name"
                label="Document name"
                placeholder="Research Notes"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <Textarea
                id="doc-text"
                label="Document text"
                placeholder="Paste the document text..."
                rows={8}
                required
                value={text}
                onChange={(e) => setText(e.target.value)}
              />

              {error && <ErrorMessage message={error} />}
              {created && (
                <p className="animate-fade-in flex items-center gap-2 rounded-md border border-border bg-secondary px-3.5 py-2.5 text-[13px] text-foreground">
                  <CheckIcon width={13} height={13} strokeWidth={1.8} className="shrink-0" />
                  {created}
                </p>
              )}

              <div className="flex items-center gap-3">
                <Button type="submit" disabled={submitting || !name.trim() || !text.trim()}>
                  {submitting ? 'Adding document...' : 'Add document'}
                </Button>
                <span className="text-[12px] text-muted-foreground">No file upload — text only.</span>
              </div>
            </form>
          </section>

          <section>
            <DocumentList documents={documents} loading={loading} />
          </section>
        </div>
      </div>
    </div>
  )
}
