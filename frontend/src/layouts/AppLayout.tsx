import type { ReactNode } from 'react'
import Sidebar, { type View } from '../components/Sidebar'

interface AppLayoutProps {
  view: View
  username: string
  navOpen: boolean
  onCloseNav: () => void
  onNavigate: (view: View) => void
  onNewChat: () => void
  onLogout: () => void
  children: ReactNode
}

/**
 * Shared page shell: desktop sidebar, slide-in mobile sidebar, and the
 * content area. Every protected route renders inside this, so the
 * sidebar never has to be duplicated or re-wired per page.
 */
export default function AppLayout({
  view,
  username,
  navOpen,
  onCloseNav,
  onNavigate,
  onNewChat,
  onLogout,
  children,
}: AppLayoutProps) {
  function navigate(next: View) {
    onNavigate(next)
    onCloseNav()
  }

  return (
    <div className="grid h-screen grid-cols-1 overflow-hidden bg-background md:grid-cols-[264px_minmax(0,1fr)]">
      <div className="hidden md:block">
        <Sidebar view={view} username={username} onNavigate={navigate} onNewChat={onNewChat} onLogout={onLogout} />
      </div>

      {navOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            aria-label="Close navigation"
            onClick={onCloseNav}
            className="animate-fade-in absolute inset-0 bg-black/25"
          />
          <div className="animate-slide-in-left absolute inset-y-0 left-0 w-[272px]">
            <Sidebar view={view} username={username} onNavigate={navigate} onNewChat={onNewChat} onLogout={onLogout} />
          </div>
        </div>
      )}

      <main className="min-w-0 overflow-hidden">{children}</main>
    </div>
  )
}