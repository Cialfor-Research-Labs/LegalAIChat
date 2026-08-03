import React from 'react';
import {
  Archive,
  BookOpen,
  Download,
  Eye,
  FileUp,
  LogOut,
  MessageSquare,
  Plus,
  RefreshCw,
  Search,
  Shield,
  Trash2,
  X,
} from 'lucide-react';

interface SidebarProps {
  onNewChat: () => void;
  onSelectChat: (sessionId: string) => void;
  onRefreshSessions: () => void;
  onRefreshMatters: () => void;
  onLogout: () => void;
  onClose: () => void;
  userName: string;
  activeSessionId: string | null;
  error: string | null;
  isSessionsLoading: boolean;
  isOpen: boolean;
  chatHistory: {
    session_id: string;
    title: string;
    created_at: string;
    updated_at: string;
  }[];
  matters: {
    matter_id: string;
    title: string;
    description: string;
    case_number: string | null;
    court: string | null;
    jurisdiction: string | null;
    stage: string | null;
    status: string;
    metadata: Record<string, unknown>;
    is_archived?: boolean;
    archived_at?: string | null;
    created_at: string;
    updated_at: string;
  }[];
  isMatterListLoading: boolean;
  matterCatalogError: string | null;
  matterId: string;
  selectedMatterId: string;
  onMatterIdChange: (value: string) => void;
  onSelectMatter: (matterId: string) => void;
  onLoadMatter: () => void;
  onMatterFileChange: (file: File | null) => void;
  onUploadMatterDocument: () => void;
  onMatterSearchChange: (value: string) => void;
  onSearchMatterDocuments: () => void;
  onRefreshMatterDocuments: () => void;
  onViewDocument: (documentId: string) => void;
  onDownloadDocument: (documentId: string) => void;
  onArchiveDocument: (documentId: string) => void;
  onDeleteDocument: (documentId: string) => void;
  selectedMatterFileName: string | null;
  isMatterLoading: boolean;
  isMatterUploading: boolean;
  isMatterSearching: boolean;
  matterError: string | null;
  matterDocuments: {
    document_id: string;
    original_filename: string;
    status: string;
    upload_timestamp: string;
    chunk_count: number;
  }[];
  matterSearchResults: {
    chunk_text: string;
    document_id: string;
    document_name: string;
    page_number: number | null;
    paragraph_number: number | null;
    chunk_position: number;
  }[];
  matterSearchQuery: string;
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

function formatMatterLabel(matter: {
  title: string;
  case_number: string | null;
  court: string | null;
  status: string;
}): string {
  const bits = [matter.title];
  if (matter.case_number) {
    bits.push(matter.case_number);
  }
  if (matter.court) {
    bits.push(matter.court);
  }
  if (matter.status) {
    bits.push(matter.status);
  }
  return bits.join(' · ');
}

function formatMatterSubtitle(matter: {
  jurisdiction: string | null;
  stage: string | null;
  updated_at: string;
}): string {
  const bits: string[] = [];
  if (matter.jurisdiction) {
    bits.push(matter.jurisdiction);
  }
  if (matter.stage) {
    bits.push(matter.stage);
  }
  bits.push(`Updated ${formatSessionDate(matter.updated_at)}`);
  return bits.join(' · ');
}

export const Sidebar: React.FC<SidebarProps> = ({
  onNewChat,
  onSelectChat,
  onRefreshSessions,
  onRefreshMatters,
  onLogout,
  onClose,
  userName,
  activeSessionId,
  error,
  isSessionsLoading,
  isOpen,
  chatHistory,
  matters,
  isMatterListLoading,
  matterCatalogError,
  matterId,
  selectedMatterId,
  onMatterIdChange,
  onSelectMatter,
  onLoadMatter,
  onMatterFileChange,
  onUploadMatterDocument,
  onMatterSearchChange,
  onSearchMatterDocuments,
  onRefreshMatterDocuments,
  onViewDocument,
  onDownloadDocument,
  onArchiveDocument,
  onDeleteDocument,
  selectedMatterFileName,
  isMatterLoading,
  isMatterUploading,
  isMatterSearching,
  matterError,
  matterDocuments,
  matterSearchResults,
  matterSearchQuery,
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
      <aside className="absolute inset-y-0 left-0 z-30 flex h-full w-72 flex-col overflow-hidden border-r border-outline-variant/20 bg-surface-container shadow-ambient md:relative md:z-0 md:shadow-none">
        <div className="shrink-0 border-b border-outline-variant/20 bg-surface-container p-4">
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

          <div className="mt-4 rounded-2xl border border-outline-variant/20 bg-surface-container-low p-3">
            <div className="mb-2 flex items-center justify-between gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-on-surface-variant">
              <div className="flex items-center gap-2">
                <FileUp size={13} />
                Matter Workspace
              </div>
              <button
                type="button"
                onClick={onRefreshMatters}
                className="inline-flex items-center gap-1 rounded-full border border-outline-variant/20 px-2 py-1 text-[11px] text-on-surface-variant transition hover:border-primary/30 hover:text-on-surface"
              >
                <RefreshCw size={12} />
                Refresh matters
              </button>
            </div>

            <div className="space-y-3">
              <div className="rounded-xl border border-outline-variant/20 bg-surface-container px-3 py-3">
                <div className="mb-2 text-xs font-medium text-on-surface-variant">
                  Choose an existing matter
                </div>
                {isMatterListLoading ? (
                  <div className="text-sm text-on-surface-variant">Loading matters...</div>
                ) : matterCatalogError ? (
                  <div className="rounded-lg border border-error/30 bg-error/10 px-3 py-2 text-xs text-error">
                    {matterCatalogError}
                  </div>
                ) : matters.length === 0 ? (
                  <div className="text-sm text-on-surface-variant">
                    No saved matters yet. Paste a matter ID below, or create one in the matters workspace.
                  </div>
                ) : (
                  <div className="max-h-44 space-y-2 overflow-y-auto pr-1">
                    {matters.map((matter) => {
                      const isActive = matter.matter_id === selectedMatterId;
                      return (
                        <button
                          key={matter.matter_id}
                          type="button"
                          onClick={() => onSelectMatter(matter.matter_id)}
                          className={[
                            'w-full rounded-xl border px-3 py-2 text-left transition',
                            isActive
                              ? 'border-primary/35 bg-primary/10 text-on-surface'
                              : 'border-outline-variant/30 bg-surface-container-low hover:border-primary/20 hover:bg-surface-container-high',
                          ].join(' ')}
                        >
                          <div className="truncate text-sm font-medium">{matter.title}</div>
                          <div className="mt-0.5 truncate text-[11px] text-on-surface-variant">
                            {formatMatterLabel(matter)}
                          </div>
                          <div className="mt-1 truncate text-[11px] text-on-surface-variant">
                            {formatMatterSubtitle(matter)}
                          </div>
                          <div className="mt-1 font-mono text-[11px] text-on-surface-variant">
                            {matter.matter_id}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-dashed border-outline-variant/30 bg-surface-container px-3 py-3">
                <label className="mb-2 block text-xs font-medium text-on-surface-variant">
                  Or paste a matter ID
                </label>
                <input
                  type="text"
                  value={matterId}
                  onChange={(event) => onMatterIdChange(event.target.value)}
                  placeholder="Matter ID"
                  className="w-full rounded-xl border border-outline-variant/30 bg-surface-container-low px-3 py-2 text-sm outline-none transition focus:border-primary/40"
                />
                <button
                  type="button"
                  onClick={onLoadMatter}
                  className="neutral-button mt-2 w-full justify-center text-sm"
                >
                  <RefreshCw size={14} />
                  {selectedMatterId ? 'Switch matter' : 'Load matter'}
                </button>
                <div className="mt-2 text-[11px] leading-5 text-on-surface-variant">
                  Use a matter from the list above, or paste the UUID if you already have it.
                </div>
                {selectedMatterId ? (
                  <div className="mt-2 rounded-lg border border-outline-variant/20 bg-surface-container-low px-3 py-2 text-[11px] text-on-surface-variant">
                    Active matter: <span className="font-mono text-on-surface">{selectedMatterId}</span>
                  </div>
                ) : null}
              </div>

              <div className="rounded-xl border border-outline-variant/20 bg-surface-container px-3 py-3 space-y-2">
                <label className="block text-xs font-medium text-on-surface-variant">
                  Upload PDF, DOCX, or TXT
                </label>
                <input
                  type="file"
                  accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
                  onChange={(event) => onMatterFileChange(event.target.files?.[0] ?? null)}
                  className="block w-full text-xs text-on-surface-variant file:mr-3 file:rounded-lg file:border-0 file:bg-primary file:px-3 file:py-2 file:text-sm file:font-semibold file:text-on-primary"
                />
                <div className="mt-2 text-[11px] text-on-surface-variant">
                  {selectedMatterFileName || 'No file selected'}
                </div>
                <button
                  type="button"
                  onClick={onUploadMatterDocument}
                  disabled={isMatterUploading || !selectedMatterId}
                  className="primary-button mt-3 w-full justify-center disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <FileUp size={16} />
                  {isMatterUploading ? 'Uploading...' : 'Upload Document'}
                </button>
              </div>

              <div className="rounded-xl border border-outline-variant/20 bg-surface-container px-3 py-3 space-y-2">
                <label className="block text-xs font-medium text-on-surface-variant">
                  Search matter documents
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={matterSearchQuery}
                    onChange={(event) => onMatterSearchChange(event.target.value)}
                    placeholder="Search text"
                    className="min-w-0 flex-1 rounded-xl border border-outline-variant/30 bg-surface-container-low px-3 py-2 text-sm outline-none transition focus:border-primary/40"
                  />
                  <button
                    type="button"
                    onClick={onSearchMatterDocuments}
                    disabled={isMatterSearching || !selectedMatterId}
                    className="neutral-button justify-center px-3 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Search size={16} />
                  </button>
                </div>
              </div>

              {matterError ? (
                <div className="rounded-xl border border-error/30 bg-error/10 px-3 py-2 text-xs text-error">
                  {matterError}
                </div>
              ) : null}

              {selectedMatterId ? (
                <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low px-3 py-2 text-xs text-on-surface-variant">
                  Selected matter: <span className="font-mono text-on-surface">{selectedMatterId}</span>
                </div>
              ) : null}
            </div>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          <div className="mb-3 flex items-center justify-between gap-2 px-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-on-surface-variant">
            <div className="flex items-center gap-2">
              <Shield size={13} />
              Encrypted Chats
            </div>
            <button
              type="button"
              onClick={onRefreshSessions}
              className="inline-flex items-center gap-1 rounded-full border border-outline-variant/20 px-2 py-1 text-[11px] text-on-surface-variant transition hover:border-primary/30 hover:text-on-surface"
            >
              <RefreshCw size={12} />
              Refresh
            </button>
          </div>

          {error ? (
            <div className="mb-3 rounded-2xl border border-error/40 bg-error/10 px-3 py-2 text-xs text-error">
              {error}
            </div>
          ) : null}

          <div className="space-y-2">
            {isSessionsLoading ? (
              <div className="rounded-2xl border border-outline-variant/40 bg-surface-container-low px-4 py-5 text-sm text-on-surface-variant">
                Loading sessions...
              </div>
            ) : (
              <>
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
              </>
            )}
          </div>

          {selectedMatterId ? (
            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between px-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-on-surface-variant">
                <span>Loaded Matter Files</span>
                <button
                  type="button"
                  onClick={onRefreshMatterDocuments}
                  className="inline-flex items-center gap-1 rounded-full border border-outline-variant/20 px-2 py-1 text-[11px] text-on-surface-variant transition hover:border-primary/30 hover:text-on-surface"
                >
                  <RefreshCw size={12} />
                  Refresh
                </button>
              </div>
              {isMatterLoading ? (
                <div className="rounded-2xl border border-outline-variant/20 bg-surface-container-low px-4 py-4 text-sm text-on-surface-variant">
                  Loading documents...
                </div>
              ) : matterDocuments.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-outline-variant/40 bg-surface-container-low px-4 py-4 text-sm text-on-surface-variant">
                  No uploaded documents for this matter yet.
                </div>
              ) : (
                <div className="space-y-2">
                  {matterDocuments.map((document) => (
                    <div
                      key={document.document_id}
                      className="rounded-2xl border border-outline-variant/25 bg-surface-container-low px-3 py-3"
                    >
                      <div className="mb-2">
                        <div className="truncate text-sm font-medium text-on-surface">
                          {document.original_filename}
                        </div>
                        <div className="text-[11px] text-on-surface-variant">
                          {document.status} · {document.chunk_count} chunks
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => onViewDocument(document.document_id)}
                          className="inline-flex items-center gap-1 rounded-full border border-outline-variant/20 px-2 py-1 text-[11px] text-on-surface-variant transition hover:border-primary/30 hover:text-on-surface"
                        >
                          <Eye size={12} />
                          View
                        </button>
                        <button
                          type="button"
                          onClick={() => onDownloadDocument(document.document_id)}
                          className="inline-flex items-center gap-1 rounded-full border border-outline-variant/20 px-2 py-1 text-[11px] text-on-surface-variant transition hover:border-primary/30 hover:text-on-surface"
                        >
                          <Download size={12} />
                          Download
                        </button>
                        <button
                          type="button"
                          onClick={() => onArchiveDocument(document.document_id)}
                          className="inline-flex items-center gap-1 rounded-full border border-outline-variant/20 px-2 py-1 text-[11px] text-on-surface-variant transition hover:border-primary/30 hover:text-on-surface"
                        >
                          <Archive size={12} />
                          Archive
                        </button>
                        <button
                          type="button"
                          onClick={() => onDeleteDocument(document.document_id)}
                          className="inline-flex items-center gap-1 rounded-full border border-error/20 px-2 py-1 text-[11px] text-error transition hover:bg-error/10"
                        >
                          <Trash2 size={12} />
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {matterSearchResults.length > 0 ? (
                <div className="space-y-2">
                  <div className="px-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-on-surface-variant">
                    Search Results
                  </div>
                  {matterSearchResults.map((result, index) => (
                    <div
                      key={`${result.document_id}-${result.chunk_position}-${index}`}
                      className="rounded-2xl border border-outline-variant/25 bg-surface-container-low px-3 py-3 text-xs"
                    >
                      <div className="mb-2 flex flex-wrap gap-2 text-[11px] text-on-surface-variant">
                        <span className="rounded-full bg-surface-container px-2 py-0.5">
                          {result.document_name}
                        </span>
                        {result.page_number !== null ? <span>Page {result.page_number}</span> : null}
                        {result.paragraph_number !== null ? <span>Paragraph {result.paragraph_number}</span> : null}
                        <span>Chunk {result.chunk_position}</span>
                      </div>
                      <div className="text-on-surface">{result.chunk_text}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="shrink-0 border-t border-outline-variant/20 bg-surface-container p-3">
          <button type="button" onClick={onLogout} className="neutral-button w-full justify-center">
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </aside>
    </>
  );
};
