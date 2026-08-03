import React, { useEffect, useState } from 'react';
import { PanelLeft } from 'lucide-react';
import { ChatContainer } from './components/ChatContainer';
import { Message } from './components/ChatMessage';
import { Sidebar } from './components/Sidebar';
import { ApiResponseError, requestBlobWithFallback, requestWithFallback } from './api';

interface ChatPageProps {
  embedded?: boolean;
  authToken: string;
  user: {
    user_id: string;
    email: string;
    full_name: string;
  };
  onLogout: () => void;
  onGenerateLegalNotice?: (caseDetails: string) => void;
  /** Called after each successful LLM response so the usage badge updates. */
  onUsageBump?: () => void;
  keyboardShortcuts?: boolean;
  showSuggestedPrompts?: boolean;
  enableDictation?: boolean;
  personalization?: {
    baseStyle: string;
    warmth: string;
    enthusiasm: string;
    headersAndLists: string;
    emoji: string;
    fastAnswers: boolean;
    customInstructions: string;
    nickname: string;
    occupation: string;
    moreAboutYou: string;
    memoryEnabled: boolean;
  };
}

interface ChatSessionSummary {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface ChatSessionDetail extends ChatSessionSummary {
  messages: {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
  }[];
}

interface ChatResponsePayload {
  response: string;
  session_id: string | null;
  recommend_legal_notice: boolean;
  notice_prefill: string | null;
}

interface MatterDocument {
  document_id: string;
  original_filename: string;
  status: string;
  upload_timestamp: string;
  chunk_count: number;
}

interface MatterSearchResult {
  chunk_text: string;
  document_id: string;
  document_name: string;
  page_number: number | null;
  paragraph_number: number | null;
  chunk_position: number;
}

async function requestChatResponse(
  authToken: string,
  query: string,
  sessionId?: string | null,
  personalization?: ChatPageProps['personalization'],
  matterId?: string | null,
): Promise<{
  responseText: string;
  sessionId: string | null;
  recommendLegalNotice: boolean;
  noticePrefill: string | null;
}> {
  const init = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({
      query,
      session_id: sessionId || null,
      matter_id: matterId || null,
      personalization,
    }),
  };

  let data: ChatResponsePayload;
  try {
    data = await requestWithFallback<ChatResponsePayload>('/chat', () => init);
  } catch (error) {
    if (error instanceof ApiResponseError && error.status === 429) {
      const detail = error.detail as { cooldown_remaining_seconds?: number } | null;
      const cooldownSeconds = detail?.cooldown_remaining_seconds ?? 0;
      const hours = Math.max(1, Math.ceil(cooldownSeconds / 3600));
      throw new Error(
        `Daily token limit reached. Chat will be available again in approximately ${hours} hour${hours !== 1 ? 's' : ''}. The countdown is shown in the header.`,
      );
    }
    throw error;
  }

  const responseText = typeof data?.response === 'string' ? data.response.trim() : '';
  if (!responseText) {
    throw new Error('Backend returned an empty response.');
  }

  return {
    responseText,
    sessionId: typeof data?.session_id === 'string' ? data.session_id : null,
    recommendLegalNotice: Boolean(data?.recommend_legal_notice),
    noticePrefill: typeof data?.notice_prefill === 'string' ? data.notice_prefill : null,
  };
}

export const ChatPage: React.FC<ChatPageProps> = ({
  embedded = false,
  authToken,
  user,
  onLogout,
  onGenerateLegalNotice,
  onUsageBump,
  keyboardShortcuts,
  showSuggestedPrompts,
  enableDictation,
  personalization,
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSessionLoading, setIsSessionLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatSessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [matterId, setMatterId] = useState('');
  const [selectedMatterId, setSelectedMatterId] = useState('');
  const [selectedMatterFile, setSelectedMatterFile] = useState<File | null>(null);
  const [matterDocuments, setMatterDocuments] = useState<MatterDocument[]>([]);
  const [matterSearchQuery, setMatterSearchQuery] = useState('');
  const [matterSearchResults, setMatterSearchResults] = useState<MatterSearchResult[]>([]);
  const [matterError, setMatterError] = useState<string | null>(null);
  const [isMatterLoading, setIsMatterLoading] = useState(false);
  const [isMatterUploading, setIsMatterUploading] = useState(false);
  const [isMatterSearching, setIsMatterSearching] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(() => {
    if (typeof window === 'undefined') {
      return true;
    }
    return window.innerWidth >= 768;
  });

  const loadSessions = async () => {
    try {
      const data = await requestWithFallback<{ sessions: ChatSessionSummary[] }>('/chat/sessions', () => ({
        method: 'GET',
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      }));
      const sessions = Array.isArray(data.sessions) ? data.sessions : [];
      setChatHistory(sessions);
      setHistoryError(null);
      return sessions;
    } catch (error) {
      setHistoryError(error instanceof Error ? error.message : 'Unable to load chat history.');
      return [];
    }
  };

  const loadSessionMessages = async (sessionId: string) => {
    setIsSessionLoading(true);
    try {
      const data = await requestWithFallback<ChatSessionDetail>(`/chat/sessions/${sessionId}`, () => ({
        method: 'GET',
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      }));
      setActiveSessionId(data.session_id);
      setMessages(
        data.messages.map((message) => ({
          id: message.id,
          role: message.role,
          content: message.content,
          animateOnMount: false,
        })),
      );
    } finally {
      setIsSessionLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    void loadSessions().then(async (sessions) => {
      if (cancelled) {
        return;
      }
      if (sessions.length > 0) {
        try {
          await loadSessionMessages(sessions[0].session_id);
        } catch (error) {
          if (!cancelled) {
            setHistoryError(error instanceof Error ? error.message : 'Unable to open chat session.');
          }
        }
      } else {
        setMessages([]);
        setActiveSessionId(null);
        setIsSessionLoading(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [authToken]);

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      animateOnMount: false,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsGenerating(true);

    let responseText = '';
    let returnedSessionId: string | null = activeSessionId;
    let recommendLegalNotice = false;
    let noticePrefill: string | null = null;

    try {
      const result = await requestChatResponse(
        authToken,
        content,
        activeSessionId,
        personalization,
        selectedMatterId,
      );
      responseText = result.responseText;
      returnedSessionId = result.sessionId;
      recommendLegalNotice = result.recommendLegalNotice;
      noticePrefill = result.noticePrefill;
      if (returnedSessionId) {
        setActiveSessionId(returnedSessionId);
      }
      await loadSessions();
      onUsageBump?.();
    } catch (error) {
      const reason = error instanceof Error ? error.message : 'Unknown backend error';
      responseText = `The trained legal chat backend is unavailable right now.\n\nDetails: ${reason}`;
    }

    const botMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: responseText,
      legalNoticePrompt: recommendLegalNotice ? noticePrefill || content : undefined,
      animateOnMount: true,
    };

    setMessages((prev) => [...prev, botMessage]);
    setIsGenerating(false);
  };

  const handleNewChat = () => {
    setMessages([]);
    setIsGenerating(false);
    setIsSessionLoading(false);
    setActiveSessionId(null);
  };

  const handleSelectSession = async (sessionId: string) => {
    try {
      await loadSessionMessages(sessionId);
      if (typeof window !== 'undefined' && window.innerWidth < 768) {
        setIsSidebarOpen(false);
      }
    } catch (error) {
      setHistoryError(error instanceof Error ? error.message : 'Unable to open chat session.');
      setIsSessionLoading(false);
    }
  };

  const loadMatterDocuments = async (targetMatterId: string) => {
    setIsMatterLoading(true);
    try {
      const documents = await requestWithFallback<MatterDocument[]>(
        `/matter-documents?matter_id=${encodeURIComponent(targetMatterId)}`,
        () => ({
          method: 'GET',
          headers: { Authorization: `Bearer ${authToken}` },
        }),
      );
      setMatterDocuments(documents);
      setMatterError(null);
    } catch (error) {
      setMatterError(error instanceof Error ? error.message : 'Unable to load matter documents.');
    } finally {
      setIsMatterLoading(false);
    }
  };

  const handleLoadMatter = () => {
    const normalizedMatterId = matterId.trim();
    if (!normalizedMatterId) {
      setMatterError('Enter a matter ID.');
      return;
    }
    setSelectedMatterId(normalizedMatterId);
    setMatterSearchResults([]);
    void loadMatterDocuments(normalizedMatterId);
  };

  const handleUploadMatterDocument = async () => {
    if (!selectedMatterId || !selectedMatterFile) {
      setMatterError('Select a matter and a document to upload.');
      return;
    }
    setIsMatterUploading(true);
    try {
      const body = new FormData();
      body.append('matter_id', selectedMatterId);
      body.append('file', selectedMatterFile);
      await requestWithFallback<MatterDocument>('/matter-documents/upload', () => ({
        method: 'POST',
        headers: { Authorization: `Bearer ${authToken}` },
        body,
      }));
      setSelectedMatterFile(null);
      setMatterError(null);
      await loadMatterDocuments(selectedMatterId);
    } catch (error) {
      setMatterError(error instanceof Error ? error.message : 'Unable to upload the document.');
    } finally {
      setIsMatterUploading(false);
    }
  };

  const handleSearchMatterDocuments = async () => {
    const normalizedQuery = matterSearchQuery.trim();
    if (!selectedMatterId || normalizedQuery.length < 2) {
      setMatterError('Enter at least two characters to search the selected matter.');
      return;
    }
    setIsMatterSearching(true);
    try {
      const result = await requestWithFallback<{ items: MatterSearchResult[] }>(
        `/matter-documents/search?matter_id=${encodeURIComponent(selectedMatterId)}&query=${encodeURIComponent(normalizedQuery)}`,
        () => ({
          method: 'GET',
          headers: { Authorization: `Bearer ${authToken}` },
        }),
      );
      setMatterSearchResults(result.items);
      setMatterError(null);
    } catch (error) {
      setMatterError(error instanceof Error ? error.message : 'Unable to search matter documents.');
    } finally {
      setIsMatterSearching(false);
    }
  };

  const handleDocumentStatusChange = async (documentId: string, action: 'archive' | 'delete') => {
    try {
      await requestWithFallback<MatterDocument>(
        action === 'archive'
          ? `/matter-documents/${documentId}/archive`
          : `/matter-documents/${documentId}`,
        () => ({
          method: action === 'archive' ? 'POST' : 'DELETE',
          headers: { Authorization: `Bearer ${authToken}` },
        }),
      );
      setMatterSearchResults((current) =>
        current.filter((result) => result.document_id !== documentId),
      );
      await loadMatterDocuments(selectedMatterId);
    } catch (error) {
      setMatterError(error instanceof Error ? error.message : `Unable to ${action} the document.`);
    }
  };

  const handleDocumentFile = async (documentId: string, disposition: 'view' | 'download') => {
    try {
      const result = await requestBlobWithFallback(
        `/matter-documents/${documentId}/${disposition}`,
        () => ({
          method: 'GET',
          headers: { Authorization: `Bearer ${authToken}` },
        }),
      );
      const objectUrl = URL.createObjectURL(result.blob);
      if (disposition === 'view') {
        window.open(objectUrl, '_blank', 'noopener,noreferrer');
      } else {
        const link = document.createElement('a');
        link.href = objectUrl;
        link.download = result.filename || 'matter-document';
        link.click();
      }
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
      setMatterError(null);
    } catch (error) {
      setMatterError(error instanceof Error ? error.message : `Unable to ${disposition} the document.`);
    }
  };

  const content = (
    <>
      <div className="sticky top-0 z-30 shrink-0 flex items-center justify-between border-b border-outline-variant/20 bg-surface-container p-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            aria-label={isSidebarOpen ? 'Collapse sidebar' : 'Open sidebar'}
            onClick={() => setIsSidebarOpen((current) => !current)}
            className="flex h-10 w-10 items-center justify-center rounded-2xl border border-outline-variant/40 bg-surface-container-low text-on-surface-variant transition hover:border-primary/30 hover:text-on-surface"
          >
            <PanelLeft size={18} />
          </button>
          <div>
          <div className="font-semibold">LAW LLM Assistant</div>
          <div className="text-xs text-on-surface-variant">{user.full_name}</div>
        </div>
        </div>
      </div>
      <ChatContainer
        messages={messages}
        isLoading={isGenerating}
        isSessionLoading={isSessionLoading}
        onSendMessage={handleSendMessage}
        onGenerateLegalNotice={onGenerateLegalNotice}
        keyboardShortcuts={keyboardShortcuts}
        showSuggestedPrompts={showSuggestedPrompts}
        enableDictation={enableDictation}
      />
    </>
  );

  return (
    <div className="relative flex h-full min-h-0 overflow-hidden bg-surface text-on-surface" data-theme="dark">
      <Sidebar
        onNewChat={handleNewChat}
        onSelectChat={handleSelectSession}
        onLogout={onLogout}
        onClose={() => setIsSidebarOpen(false)}
        userName={user.full_name}
        chatHistory={chatHistory}
        activeSessionId={activeSessionId}
        error={historyError}
        isOpen={isSidebarOpen}
        matterId={matterId}
        selectedMatterId={selectedMatterId}
        onMatterIdChange={setMatterId}
        onLoadMatter={handleLoadMatter}
        onMatterFileChange={setSelectedMatterFile}
        onUploadMatterDocument={() => void handleUploadMatterDocument()}
        onMatterSearchChange={setMatterSearchQuery}
        onSearchMatterDocuments={() => void handleSearchMatterDocuments()}
        onRefreshMatterDocuments={() => void loadMatterDocuments(selectedMatterId)}
        onViewDocument={(documentId) => void handleDocumentFile(documentId, 'view')}
        onDownloadDocument={(documentId) => void handleDocumentFile(documentId, 'download')}
        onArchiveDocument={(documentId) => void handleDocumentStatusChange(documentId, 'archive')}
        onDeleteDocument={(documentId) => void handleDocumentStatusChange(documentId, 'delete')}
        selectedMatterFileName={selectedMatterFile?.name ?? null}
        isMatterLoading={isMatterLoading}
        isMatterUploading={isMatterUploading}
        isMatterSearching={isMatterSearching}
        matterError={matterError}
        matterDocuments={matterDocuments}
        matterSearchResults={matterSearchResults}
        matterSearchQuery={matterSearchQuery}
      />
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">{content}</div>
    </div>
  );
};

export default ChatPage;
