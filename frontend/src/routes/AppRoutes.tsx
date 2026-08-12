import { useState } from 'react'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import type { View } from '../components/Sidebar'
import { useDocuments } from '../hooks/useDocuments'
import { useSession } from '../hooks/useSession'
import AppLayout from '../layouts/AppLayout'
import AgentPage from '../pages/AgentPage'
import AnswerPage, { type Turn } from '../pages/AnswerPage'
import DocumentsPage from '../pages/DocumentsPage'
import LoginPage from '../pages/LoginPage'
import ProtectedRoute from './ProtectedRoute'

const PATH_BY_VIEW: Record<View, string> = { chat: '/', documents: '/documents', agent: '/agent' }
const VIEW_BY_PATH: Record<string, View> = { '/': 'chat', '/documents': 'documents', '/agent': 'agent' }

/**
 * Everything behind the sidebar: shared chat/document/session state,
 * plus the inner route tree that decides which page sits inside the
 * shell. Split out from AppRoutes so ProtectedRoute only has to guard
 * one element, not three separate ones.
 */
function AuthenticatedApp({ username, onLogout }: { username: string; onLogout: () => void }) {
  const navigate = useNavigate()
  const location = useLocation()
  const view = VIEW_BY_PATH[location.pathname] ?? 'chat'

  const { documents, loading: documentsLoading, refresh: refreshDocuments } = useDocuments(true)

  const [navOpen, setNavOpen] = useState(false)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [topK, setTopK] = useState(4)
  const [retrievalMode, setRetrievalMode] = useState('tfidf')
  const [pipelineMode, setPipelineMode] = useState('custom')
  const [turns, setTurns] = useState<Turn[]>([])

  function toggleSource(id: string) {
    setSelectedIds((ids) => (ids.includes(id) ? ids.filter((v) => v !== id) : [...ids, id]))
  }

  function startNewChat() {
    setTurns([])
    navigate('/')
  }

  return (
    <AppLayout
      view={view}
      username={username}
      navOpen={navOpen}
      onCloseNav={() => setNavOpen(false)}
      onNavigate={(next) => navigate(PATH_BY_VIEW[next])}
      onNewChat={startNewChat}
      onLogout={onLogout}
    >
      <Routes>
        <Route
          index
          element={
            <AnswerPage
              documents={documents}
              selectedIds={selectedIds}
              onToggleSource={toggleSource}
              topK={topK}
              onTopKChange={setTopK}
              retrievalMode={retrievalMode}
              onRetrievalModeChange={setRetrievalMode}
              pipelineMode={pipelineMode}
              onPipelineModeChange={setPipelineMode}
              turns={turns}
              onTurnsChange={setTurns}
              onManageDocuments={() => navigate('/documents')}
              onOpenNav={() => setNavOpen(true)}
            />
          }
        />
        <Route
          path="documents"
          element={
            <DocumentsPage
              documents={documents}
              loading={documentsLoading}
              onRefresh={refreshDocuments}
              onOpenNav={() => setNavOpen(true)}
            />
          }
        />
        <Route path="agent" element={<AgentPage onOpenNav={() => setNavOpen(true)} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppLayout>
  )
}

/**
 * Top-level route tree: /login is public, everything else requires a
 * session (enforced by ProtectedRoute) and lives inside AuthenticatedApp.
 */
export default function AppRoutes() {
  const { username, setUsername, signOut } = useSession()

  return (
    <Routes>
      <Route
        path="/login"
        element={username ? <Navigate to="/" replace /> : <LoginPage onSignedIn={setUsername} />}
      />
      <Route element={<ProtectedRoute username={username} />}>
        <Route path="/*" element={<AuthenticatedApp username={username as string} onLogout={signOut} />} />
      </Route>
    </Routes>
  )
}