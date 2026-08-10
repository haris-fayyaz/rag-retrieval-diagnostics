import type { ReactNode } from 'react'
import { AgentIcon, AppMark, ChatIcon, DocumentIcon, LogoutIcon, PlusIcon } from './icons'

export type View = 'chat' | 'documents' | 'agent'

export function NewChatButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="group flex h-11 w-full items-center gap-2.5 rounded-md border border-border bg-background px-3 text-sm font-medium text-foreground transition-colors duration-150 hover:border-[#d0d0d0] hover:bg-secondary md:h-10"
    >
      <PlusIcon className="text-subtle-foreground transition-colors group-hover:text-foreground" />
      New chat
    </button>
  )
}

export function NavigationItem({
  icon,
  label,
  active = false,
  muted = false,
  onClick,
}: {
  icon?: ReactNode
  label: string
  active?: boolean
  muted?: boolean
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      disabled={muted}
      className={`relative flex h-11 w-full items-center gap-2.5 rounded-md px-2.5 text-left text-[13.5px] transition-colors duration-150 md:h-9 ${
        active
          ? 'bg-secondary font-medium text-foreground'
          : muted
            ? 'cursor-default text-[#a3a3a3]'
            : 'text-subtle-foreground hover:bg-secondary hover:text-foreground'
      }`}
    >
      {active && (
        <span className="absolute left-0 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-full bg-foreground" />
      )}
      {icon && <span className={active ? 'text-foreground' : 'text-[#9a9a9a]'}>{icon}</span>}
      <span className="truncate">{label}</span>
    </button>
  )
}

export default function Sidebar({
  view,
  username,
  onNavigate,
  onNewChat,
  onLogout,
}: {
  view: View
  username: string
  onNavigate: (view: View) => void
  onNewChat: () => void
  onLogout: () => void
}) {
  return (
    <aside className="flex h-full w-full flex-col border-r border-border bg-muted">
      <div className="flex items-center gap-2.5 px-4 pb-4 pt-5">
        <AppMark className="text-primary" />
        <span className="text-[15px] font-semibold tracking-[-0.01em]">RAG Assistant</span>
      </div>

      <div className="px-3 pb-4">
        <NewChatButton onClick={onNewChat} />
      </div>

      <nav className="flex flex-col gap-0.5 px-3">
        <NavigationItem
          icon={<ChatIcon />}
          label="Chat"
          active={view === 'chat'}
          onClick={() => onNavigate('chat')}
        />
        <NavigationItem
          icon={<AgentIcon />}
          label="Agent query"
          active={view === 'agent'}
          onClick={() => onNavigate('agent')}
        />
        <NavigationItem
          icon={<DocumentIcon />}
          label="Documents"
          active={view === 'documents'}
          onClick={() => onNavigate('documents')}
        />
      </nav>

      {/* Structure reserved for conversation history. History itself is not
          part of the current implementation. */}
      <div className="mt-7 flex min-h-0 flex-1 flex-col px-3">
        <p className="label-caps px-2.5 pb-2">Recent</p>
        <div className="scroll-quiet min-h-0 flex-1 overflow-y-auto">
          <div className="mx-2.5 rounded-md border border-dashed border-border px-3 py-4">
            <p className="text-[12.5px] leading-relaxed text-muted-foreground">
              Conversations are not saved yet. Your chat stays here until you start a new one.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 border-t border-border px-3 py-3">
        <div className="flex items-center gap-2.5 px-1.5 py-1">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-[11px] font-semibold uppercase text-primary-foreground">
            {username.slice(0, 2)}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[11px] uppercase tracking-[0.08em] text-muted-foreground">
              Signed in as
            </p>
            <p className="truncate text-[13px] font-medium">{username}</p>
          </div>
          <button
            onClick={onLogout}
            title="Log out"
            aria-label="Log out"
            className="flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground md:h-8 md:w-8"
          >
            <LogoutIcon />
          </button>
        </div>
      </div>
    </aside>
  )
}
