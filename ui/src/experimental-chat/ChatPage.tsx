import React, { useEffect, useState } from 'react';
import { PanelLeft } from 'lucide-react';
import { ChatContainer } from './components/ChatContainer';
import { Message } from './components/ChatMessage';
import { Sidebar } from './components/Sidebar';
import { requestWithFallback } from './api';

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

async function requestChatResponse(
  authToken: string,
  query: string,
  sessionId?: string | null,
  personalization?: ChatPageProps['personalization'],
): Promise<{
  responseText: string;
  sessionId: string | null;
  recommendLegalNotice: boolean;
  noticePrefill: string | null;
}> {
  const url = '/chat';
  const init = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({ query, session_id: sessionId || null, personalization }),
  };

  // Use fetch directly so we can inspect the status code for 429.
  let rawResponse: Response | null = null;
  try {
    rawResponse = await fetch(url, init);
  } catch {
    // network error — fall through to requestWithFallback below
  }

  if (rawResponse && rawResponse.status === 429) {
    let cooldownSeconds = 0;
    try {
      const body = await rawResponse.json();
      cooldownSeconds = body?.detail?.cooldown_remaining_seconds ?? 0;
    } catch { /* ignore */ }
    const hours = Math.ceil(cooldownSeconds / 3600);
    throw new Error(
      `Daily token limit reached. Chat will be available again in approximately ${hours} hour${hours !== 1 ? 's' : ''}. The countdown is shown in the header.`,
    );
  }

  const data = await requestWithFallback<ChatResponsePayload>('/chat', () => init);

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
      const result = await requestChatResponse(authToken, content, activeSessionId, personalization);
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
      />
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">{content}</div>
    </div>
  );
};

export default ChatPage;
