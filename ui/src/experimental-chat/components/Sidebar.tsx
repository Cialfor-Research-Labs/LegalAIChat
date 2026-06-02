import React from 'react';
import { BookOpen, LogOut, MessageSquare, Plus, Shield, X } from 'lucide-react';

interface SidebarProps {
  onNewChat: () => void;
  onSelectChat: (sessionId: string) => void;
  onLogout: () => void;
  onClose: () => void;
  userName: string;
  activeSessionId: string | null;
  error: string | null;
  isOpen: boolean;
  chatHistory: {
    session_id: string;
    title: string;
    created_at: string;
    updated_at: string;
  }[];
}

function formatSessionDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? 'Unknown'
    : date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
      });
}

export const Sidebar: React.FC<SidebarProps> = ({
  onNewChat,
  onSelectChat,
  onLogout,
  onClose,
  userName,
  activeSessionId,
  error,
  isOpen,
  chatHistory,
}) => {
  if (!isOpen) {
    return null;
  }

  return (
    <>
      <button
        type="button"
        aria-label="Close sidebar"
        onClick={onClose}
        className="fixed inset-0 z-20 bg-black/30 backdrop-blur-[1px] md:hidden"
      />
      <aside className="absolute inset-y-0 left-0 z-30 flex h-full w-72 flex-col border-r border-outline-variant/20 bg-surface-container shadow-ambient md:relative md:z-0 md:shadow-none">
      <div className="border-b border-outline-variant/20 p-4">
        <div className="mb-4 flex items-center justify-between md:hidden">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-on-surface-variant">
            Sidebar
          </div>
          <button
            type="button"
            aria-label="Close sidebar"
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-outline-variant/40 bg-surface-container-low text-on-surface-variant transition hover:text-on-surface"
          >
            <X size={16} />
          </button>
        </div>
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary text-on-primary">
            <BookOpen size={18} />
          </div>
          <div>
            <div className="text-sm font-semibold text-on-surface">LAW LLM Workspace</div>
            <div className="text-xs text-on-surface-variant">{userName}</div>
          </div>
        </div>

        <button onClick={onNewChat} className="primary-button w-full justify-center">
          <Plus size={16} />
          New Session
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        <div className="mb-3 flex items-center gap-2 px-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-on-surface-variant">
          <Shield size={13} />
          Encrypted Chats
        </div>

        {error ? (
          <div className="mb-3 rounded-2xl border border-error/40 bg-error/10 px-3 py-2 text-xs text-error">
            {error}
          </div>
        ) : null}

        <div className="space-y-2">
          {chatHistory.map((chat) => {
            const isActive = chat.session_id === activeSessionId;
            return (
              <button
                key={chat.session_id}
                type="button"
                onClick={() => onSelectChat(chat.session_id)}
                className={[
                  'w-full rounded-2xl border px-3 py-3 text-left transition',
                  isActive
                    ? 'border-primary/35 bg-primary/10 text-on-surface'
                    : 'border-outline-variant/30 bg-surface-container-low hover:border-primary/20 hover:bg-surface-container-high',
                ].join(' ')}
              >
                <div className="mb-1 flex items-start gap-3">
                  <MessageSquare size={16} className="mt-0.5 flex-shrink-0 text-primary" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{chat.title}</div>
                    <div className="text-xs text-on-surface-variant">
                      Updated {formatSessionDate(chat.updated_at)}
                    </div>
                  </div>
                </div>
              </button>
            );
          })}

          {chatHistory.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-outline-variant/40 bg-surface-container-low px-4 py-5 text-sm text-on-surface-variant">
              No saved sessions yet. Start a new conversation to create one.
            </div>
          ) : null}
        </div>
      </div>

      <div className="border-t border-outline-variant/20 p-3">
        <button type="button" onClick={onLogout} className="neutral-button w-full justify-center">
          <LogOut size={16} />
          Logout
        </button>
      </div>
    </aside>
    </>
  );
};
