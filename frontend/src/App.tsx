import { useCallback, useEffect, useState } from 'react'
import { api, getSession, setUnauthorizedHandler, type Document } from './api/client'
import Sidebar, { type View } from './components/Sidebar'
import AgentPage from './pages/AgentPage'
import AnswerPage, { type Turn } from './pages/AnswerPage'
import DocumentsPage from './pages/DocumentsPage'
import LoginPage from './pages/LoginPage'

export default function App() {
  const [username, setUsername] = useState<string | null>(() => getSession()?.username ?? null)
  const [view, setView] = useState<View>('chat')
  const [navOpen, setNavOpen] = useState(false)

  const [documents, setDocuments] = useState<Document[]>([])
  const [documentsLoading, setDocumentsLoading] = useState(false)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [topK, setTopK] = useState(4)
  const [turns, setTurns] = useState<Turn[]>([])

  const refreshDocuments = useCallback(async () => {
    setDocumentsLoading(true)
    try {
      setDocuments(await api.listDocuments())
    } catch {
      setDocuments([])
    } finally {
      setDocumentsLoading(false)
    }
  }, [])

  // A 401 raised anywhere in the app drops straight back to the login screen.
  useEffect(() => {
    setUnauthorizedHandler(() => setUsername(null))
    return () => setUnauthorizedHandler(null)
  }, [])

  useEffect(() => {
    if (username) void refreshDocuments()
  }, [username, refreshDocuments])

  if (!username) return <LoginPage onSignedIn={setUsername} />

  function signOut() {
    api.logout()
    setUsername(null)
    setTurns([])
    setSelectedIds([])
  }

  function navigate(next: View) {
    setView(next)
    setNavOpen(false)
  }

  function startNewChat() {
    setTurns([])
    navigate('chat')
  }

  function toggleSource(id: string) {
    setSelectedIds((ids) => (ids.includes(id) ? ids.filter((v) => v !== id) : [...ids, id]))
  }

  return (
    <div className="grid h-screen grid-cols-1 overflow-hidden bg-background md:grid-cols-[264px_minmax(0,1fr)]">
      <div className="hidden md:block">
        <Sidebar
          view={view}
          username={username}
          onNavigate={navigate}
          onNewChat={startNewChat}
          onLogout={signOut}
        />
      </div>

      {navOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            aria-label="Close navigation"
            onClick={() => setNavOpen(false)}
            className="absolute inset-0 bg-black/25"
          />
          <div className="absolute inset-y-0 left-0 w-[272px]">
            <Sidebar
              view={view}
              username={username}
              onNavigate={navigate}
              onNewChat={startNewChat}
              onLogout={signOut}
            />
          </div>
        </div>
      )}

      <main className="min-w-0 overflow-hidden">
        {view === 'chat' && (
          <AnswerPage
            documents={documents}
            selectedIds={selectedIds}
            onToggleSource={toggleSource}
            topK={topK}
            onTopKChange={setTopK}
            turns={turns}
            onTurnsChange={setTurns}
            onManageDocuments={() => navigate('documents')}
            onOpenNav={() => setNavOpen(true)}
          />
        )}
        {view === 'documents' && (
          <DocumentsPage
            documents={documents}
            loading={documentsLoading}
            onRefresh={refreshDocuments}
            onOpenNav={() => setNavOpen(true)}
          />
        )}
        {view === 'agent' && <AgentPage onOpenNav={() => setNavOpen(true)} />}
      </main>
    </div>
  )
}
