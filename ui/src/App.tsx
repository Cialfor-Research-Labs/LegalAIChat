import React, { useEffect, useRef, useState } from 'react';
import {
  Check,
  ChevronRight,
  FilePenLine,
  FileText,
  HelpCircle,
  LogOut,
  MessageSquare,
  Plus,
  Settings,
  Sliders,
  Sparkles,
  User,
  X,
} from 'lucide-react';
import { AuthFormValue, AuthPage } from './auth/AuthPage';
import { DocumentDraft, DocumentGenerator, type DocumentGeneratorInput } from './DocumentGenerator';
import { getDocumentSkillByType } from './documentSkills';
import ChatPage from './experimental-chat/ChatPage';
import { requestWithFallback } from './experimental-chat/api';
import { LegalNoticeDraft, LegalNoticeGenerator } from './LegalNoticeGenerator';
import { TokenUsageBadge } from './TokenUsageBadge';

type ActiveTab = 'chat' | 'legal-notice' | 'document-generator';
type AuthMode = 'login' | 'register';

interface AuthUser {
  user_id: string;
  email: string;
  full_name: string;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

interface DocumentGeneratorResponse {
  document?: string;
  draft?: string;
  content?: string;
  history_id?: string;
}

interface LegalNoticeResponse {
  notice?: string;
  history_id?: string;
}

interface GeneratorHistoryItem {
  artifact_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

const LEGAL_NOTICE_PROXY_URL = '/tllac-api/legal-notice/generate';
const LOCAL_LEGAL_NOTICE_URL = 'http://127.0.0.1:9001/legal-notice/generate';
const AUTH_TOKEN_STORAGE_KEY = 'tllac_auth_token';
const DOCUMENT_GENERATOR_PATH = '/document-generator/generate';

function getHostBasedLegalNoticeUrl(): string {
  const { protocol, hostname } = window.location;
  const resolvedProtocol = protocol === 'https:' ? 'https:' : 'http:';
  const resolvedHostname = hostname || '127.0.0.1';
  return `${resolvedProtocol}//${resolvedHostname}:9001/legal-notice/generate`;
}

async function requestLegalNotice(
  authToken: string,
  input: Omit<LegalNoticeDraft, 'notice'>,
): Promise<LegalNoticeResponse> {
  const candidateUrls = [
    LEGAL_NOTICE_PROXY_URL,
    getHostBasedLegalNoticeUrl(),
    LOCAL_LEGAL_NOTICE_URL,
  ];
  let lastError: unknown = null;

  for (const url of candidateUrls) {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          client_details: input.clientDetails,
          lawyer_details: input.lawyerDetails,
          recipient_details: input.recipientDetails,
          case_details: input.caseDetails,
          relevant_info: input.relevantInfo,
        }),
      });

      if (!response.ok) {
        throw new Error(`Generator error: ${response.status}`);
      }

      const data = await response.json();
      const notice = typeof data?.notice === 'string' ? data.notice.trim() : '';
      if (!notice) {
        throw new Error('Generator returned an empty notice.');
      }
      return {
        notice,
        history_id: typeof data?.history_id === 'string' ? data.history_id : null,
      };
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError instanceof Error ? lastError : new Error('Unable to reach legal notice generator.');
}

function getUserInitials(name?: string, email?: string): string {
  if (name && name.trim()) {
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return parts[0].slice(0, 2).toUpperCase();
  }
  if (email && email.trim()) {
    return email.trim().slice(0, 2).toUpperCase();
  }
  return 'MV';
}

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('chat');
  const [noticeDraft, setNoticeDraft] = useState<LegalNoticeDraft | null>(null);
  const [documentDraft, setDocumentDraft] = useState<DocumentDraft | null>(null);
  const [noticeHistory, setNoticeHistory] = useState<GeneratorHistoryItem[]>([]);
  const [documentHistory, setDocumentHistory] = useState<GeneratorHistoryItem[]>([]);
  const [activeNoticeHistoryId, setActiveNoticeHistoryId] = useState<string | null>(null);
  const [activeDocumentHistoryId, setActiveDocumentHistoryId] = useState<string | null>(null);
  const [initialCaseDetails, setInitialCaseDetails] = useState('');
  const [isGeneratingNotice, setIsGeneratingNotice] = useState(false);
  const [isGeneratingDocument, setIsGeneratingDocument] = useState(false);
  const [noticeError, setNoticeError] = useState<string | null>(null);
  const [documentError, setDocumentError] = useState<string | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(
    () => window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY),
  );
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(Boolean(authToken));
  const [isSubmittingAuth, setIsSubmittingAuth] = useState(false);
  // Increment after every LLM call so the usage badge re-fetches immediately
  const [usageRefreshKey, setUsageRefreshKey] = useState(0);
  const bumpUsage = () => setUsageRefreshKey((k) => k + 1);

  // Profile dropdown & modal state
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [isAccountSubMenuOpen, setIsAccountSubMenuOpen] = useState(false);
  const [activeModal, setActiveModal] = useState<'profile' | 'settings' | 'personalization' | 'upgrade' | 'help' | null>(null);
  const profileMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target as Node)) {
        setIsProfileMenuOpen(false);
        setIsAccountSubMenuOpen(false);
      }
    };

    if (isProfileMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isProfileMenuOpen]);

  useEffect(() => {
    if (!authToken) {
      setCurrentUser(null);
      setIsAuthLoading(false);
      return;
    }

    let cancelled = false;
    setIsAuthLoading(true);

    void requestWithFallback<{ user: AuthUser }>('/auth/me', () => ({
      method: 'GET',
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    }))
      .then((data) => {
        if (!cancelled) {
          setCurrentUser(data.user);
          setAuthError(null);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setAuthToken(null);
          window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
          setCurrentUser(null);
          setAuthError(error instanceof Error ? error.message : 'Authentication failed.');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsAuthLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [authToken]);

  const loadNoticeHistory = async (token: string) => {
    const data = await requestWithFallback<{ items: GeneratorHistoryItem[] }>('/legal-notice/history', () => ({
      method: 'GET',
      headers: { Authorization: `Bearer ${token}` },
    }));
    setNoticeHistory(Array.isArray(data.items) ? data.items : []);
  };

  const loadDocumentHistory = async (token: string) => {
    const data = await requestWithFallback<{ items: GeneratorHistoryItem[] }>('/document-generator/history', () => ({
      method: 'GET',
      headers: { Authorization: `Bearer ${token}` },
    }));
    setDocumentHistory(Array.isArray(data.items) ? data.items : []);
  };

  useEffect(() => {
    if (!authToken) {
      setNoticeHistory([]);
      setDocumentHistory([]);
      setActiveNoticeHistoryId(null);
      setActiveDocumentHistoryId(null);
      return;
    }

    void loadNoticeHistory(authToken);
    void loadDocumentHistory(authToken);
  }, [authToken]);

  const handleAuthSubmit = async (mode: AuthMode, form: AuthFormValue) => {
    setIsSubmittingAuth(true);
    setAuthError(null);
    try {
      const endpoint = mode === 'login' ? '/auth/login' : '/auth/register';
      const payload =
        mode === 'login'
          ? { email: form.email, password: form.password }
          : { full_name: form.fullName, email: form.email, password: form.password };
      const data = await requestWithFallback<AuthResponse>(endpoint, () => ({
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      }));
      setAuthToken(data.access_token);
      setCurrentUser(data.user);
      window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, data.access_token);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'Authentication failed.');
    } finally {
      setIsSubmittingAuth(false);
    }
  };

  const handleLogout = () => {
    setAuthToken(null);
    setCurrentUser(null);
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    setActiveTab('chat');
  };

  const createNewNotice = () => {
    setActiveTab('legal-notice');
    setNoticeDraft(null);
    setActiveNoticeHistoryId(null);
    setInitialCaseDetails('');
    setNoticeError(null);
  };

  const createNewDocument = () => {
    setActiveTab('document-generator');
    setDocumentDraft(null);
    setActiveDocumentHistoryId(null);
    setDocumentError(null);
  };

  const generateNotice = async (input: Omit<LegalNoticeDraft, 'notice'>) => {
    if (!authToken) {
      setNoticeError('Login required before generating a legal notice.');
      return;
    }

    setActiveTab('legal-notice');
    setInitialCaseDetails(input.caseDetails);
    setIsGeneratingNotice(true);
    setNoticeError(null);

    try {
      const result = await requestLegalNotice(authToken, input);
      const notice = typeof result.notice === 'string' ? result.notice : '';
      setNoticeDraft({ ...input, notice });
      setActiveNoticeHistoryId(typeof result.history_id === 'string' ? result.history_id : null);
      await loadNoticeHistory(authToken);
      bumpUsage();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to generate legal notice.';
      setNoticeError(message);
    } finally {
      setIsGeneratingNotice(false);
    }
  };

  const generateNoticeFromChat = async (caseDetails: string) => {
    await generateNotice({
      clientDetails: '',
      lawyerDetails: '',
      recipientDetails: '',
      caseDetails,
      relevantInfo:
        'Generated from the legal chat conversation. Fill missing client, lawyer, recipient, address, date, amount, and document details before dispatch.',
    });
  };

  const generateDocument = async (input: DocumentGeneratorInput) => {
    if (!authToken) {
      setDocumentError('Login required before generating a document.');
      return;
    }

    setActiveTab('document-generator');
    setIsGeneratingDocument(true);
    setDocumentError(null);

    try {
      const selectedSkill = getDocumentSkillByType(input.documentType);
      if (!selectedSkill) {
        throw new Error('Please choose a supported document type.');
      }

      const data = await requestWithFallback<DocumentGeneratorResponse>(
        DOCUMENT_GENERATOR_PATH,
        () => ({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${authToken}`,
          },
          body: JSON.stringify({
            document_type: input.documentType,
            document_type_label: selectedSkill.label,
            party_details: input.partyDetails,
            recipient_details: input.recipientDetails,
            case_details: input.caseDetails,
            relevant_info: input.relevantInfo,
            additional_info: input.additionalInfo,
            structured_fields: input.structuredFields,
            structured_sections: input.structuredSections,
            skill_name: selectedSkill.skillName,
            skill_prompt: selectedSkill.skillContent,
            frontend_source: 'document-generator',
          }),
        }),
      );

      const document =
        typeof data.document === 'string'
          ? data.document.trim()
          : typeof data.draft === 'string'
            ? data.draft.trim()
            : typeof data.content === 'string'
              ? data.content.trim()
              : '';

      if (!document) {
        throw new Error('Document generator returned an empty draft.');
      }

      setDocumentDraft({
        documentType: input.documentType,
        additionalInfo: input.additionalInfo,
        structuredFields: input.structuredFields,
        structuredSections: input.structuredSections,
        document,
      });
      setActiveDocumentHistoryId(typeof data.history_id === 'string' ? data.history_id : null);
      await loadDocumentHistory(authToken);
      bumpUsage();
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : 'Unable to prepare document draft.');
    } finally {
      setIsGeneratingDocument(false);
    }
  };

  const selectNoticeHistory = async (artifactId: string) => {
    if (!authToken) {
      return;
    }

    const data = await requestWithFallback<{
      artifact_id: string;
      input_payload: {
        client_details?: string;
        lawyer_details?: string;
        recipient_details?: string;
        case_details?: string;
        relevant_info?: string;
      };
      output_text: string;
    }>(`/legal-notice/history/${artifactId}`, () => ({
      method: 'GET',
      headers: { Authorization: `Bearer ${authToken}` },
    }));

    setActiveTab('legal-notice');
    setActiveNoticeHistoryId(data.artifact_id);
    setNoticeDraft({
      clientDetails: data.input_payload.client_details || '',
      lawyerDetails: data.input_payload.lawyer_details || '',
      recipientDetails: data.input_payload.recipient_details || '',
      caseDetails: data.input_payload.case_details || '',
      relevantInfo: data.input_payload.relevant_info || '',
      notice: data.output_text || '',
    });
  };

  const selectDocumentHistory = async (artifactId: string) => {
    if (!authToken) {
      return;
    }

    const data = await requestWithFallback<{
      artifact_id: string;
      input_payload: {
        document_type?: string;
        additional_info?: string;
        structured_fields?: Record<string, string>;
        structured_sections?: DocumentDraft['structuredSections'];
      };
      output_text: string;
    }>(`/document-generator/history/${artifactId}`, () => ({
      method: 'GET',
      headers: { Authorization: `Bearer ${authToken}` },
    }));

    setActiveTab('document-generator');
    setActiveDocumentHistoryId(data.artifact_id);
    setDocumentDraft({
      documentType: data.input_payload.document_type || '',
      additionalInfo: data.input_payload.additional_info || '',
      structuredFields: data.input_payload.structured_fields || {},
      structuredSections: data.input_payload.structured_sections || [],
      document: data.output_text || '',
    });
  };

  const tabClass = (tab: ActiveTab) =>
    [
      'inline-flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-semibold transition',
      activeTab === tab
        ? 'border-primary text-primary'
        : 'border-transparent text-on-surface-variant hover:text-on-surface',
    ].join(' ');

  if (isAuthLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface text-on-surface" data-theme="dark">
        <div className="status-pill">Checking your secure workspace...</div>
      </div>
    );
  }

  if (!authToken || !currentUser) {
    return (
      <AuthPage
        onSubmit={handleAuthSubmit}
        isSubmitting={isSubmittingAuth}
        error={authError}
      />
    );
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-surface font-body text-on-surface" data-theme="dark">
      <div className="sticky top-0 z-40 border-b border-outline-variant/20 bg-surface-container">
        <div className="flex h-14 items-center justify-between px-4 md:px-6">
          {/* Left section: Email & Token Usage Badge */}
          <div className="flex items-center gap-4 min-w-0 shrink-0">
            <div className="hidden text-sm font-medium text-on-surface-variant md:block truncate max-w-[180px]" title={currentUser.email}>
              {currentUser.email}
            </div>
            <TokenUsageBadge authToken={authToken} refreshKey={usageRefreshKey} />
          </div>

          {/* Center section: The 3 Navigation Tabs (Text only) */}
          <div className="flex items-center justify-center gap-1 mx-auto">
            <button type="button" onClick={() => setActiveTab('chat')} className={tabClass('chat')}>
              Legal Chat
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('legal-notice')}
              className={tabClass('legal-notice')}
            >
              Legal Notice Generator
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('document-generator')}
              className={tabClass('document-generator')}
            >
              Document Generator
            </button>
          </div>

          {/* Right section: Profile / Avatar Settings Dropdown */}
          <div className="relative flex items-center justify-end shrink-0" ref={profileMenuRef}>
            <button
              type="button"
              aria-label="User profile and settings"
              onClick={() => {
                setIsProfileMenuOpen((prev) => !prev);
                setIsAccountSubMenuOpen(false);
              }}
              className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-purple-600 to-indigo-600 text-sm font-bold text-white shadow-md ring-2 ring-purple-500/20 transition hover:ring-purple-500/50 hover:scale-105 active:scale-95"
            >
              {getUserInitials(currentUser.full_name, currentUser.email)}
            </button>

            {/* Profile Dropdown Menu matching Picture 2 */}
            {isProfileMenuOpen && (
              <div className="absolute right-0 top-full mt-2 w-72 rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-2 shadow-2xl z-50 animate-in fade-in zoom-in-95 duration-150 text-on-surface">
                {/* Account card / switcher header */}
                <div
                  onClick={() => setIsAccountSubMenuOpen((prev) => !prev)}
                  className="flex items-center justify-between rounded-xl p-2.5 transition hover:bg-surface-container-low cursor-pointer select-none"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-purple-600 text-sm font-semibold text-white shadow-sm">
                      {getUserInitials(currentUser.full_name, currentUser.email)}
                    </div>
                    <div className="flex flex-col text-left">
                      <span className="text-sm font-semibold text-on-surface line-clamp-1">
                        {currentUser.full_name || currentUser.email}
                      </span>
                      <span className="text-xs text-on-surface-variant">Free</span>
                    </div>
                  </div>
                  <ChevronRight size={16} className={`text-on-surface-variant transition-transform duration-200 ${isAccountSubMenuOpen ? 'rotate-90' : ''}`} />
                </div>

                {/* Account Sub-menu popover matching Picture 2 */}
                {isAccountSubMenuOpen && (
                  <div className="my-1 rounded-xl border border-outline-variant/30 bg-surface-container-high/90 p-2.5 text-xs space-y-2 animate-in fade-in duration-100 shadow-lg">
                    {/* Top email header */}
                    <div className="flex items-center gap-2 px-1 text-on-surface-variant font-medium text-[11px] truncate">
                      <User size={14} className="shrink-0 text-on-surface-variant" />
                      <span className="truncate" title={currentUser.email}>{currentUser.email}</span>
                    </div>

                    {/* Active account row with avatar & checkmark */}
                    <div className="flex items-center justify-between px-2 py-2 rounded-lg bg-surface-container-lowest border border-outline-variant/20 shadow-sm">
                      <div className="flex items-center gap-2.5 overflow-hidden">
                        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-purple-600 text-xs font-bold text-white shrink-0">
                          {getUserInitials(currentUser.full_name, currentUser.email)}
                        </div>
                        <span className="truncate text-on-surface font-semibold text-xs">{currentUser.full_name || currentUser.email}</span>
                      </div>
                      <Check size={16} className="text-primary shrink-0 font-bold" />
                    </div>

                    {/* Add account button */}
                    <button
                      type="button"
                      onClick={() => {
                        handleLogout();
                      }}
                      className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-on-surface hover:bg-surface-container-lowest transition text-left font-medium"
                    >
                      <Plus size={15} />
                      <span>Add account</span>
                    </button>
                  </div>
                )}

                <div className="my-1.5 h-px bg-outline-variant/20" />

                {/* Main Menu Options matching Picture 2 */}
                <div className="space-y-0.5 text-sm">
                  <button
                    type="button"
                    onClick={() => {
                      setActiveModal('upgrade');
                      setIsProfileMenuOpen(false);
                    }}
                    className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left font-medium text-on-surface hover:bg-surface-container-low transition"
                  >
                    <Sparkles size={16} className="text-amber-400" />
                    <span>Upgrade plan</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setActiveModal('personalization');
                      setIsProfileMenuOpen(false);
                    }}
                    className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left font-medium text-on-surface hover:bg-surface-container-low transition"
                  >
                    <Sliders size={16} className="text-on-surface-variant" />
                    <span>Personalization</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setActiveModal('profile');
                      setIsProfileMenuOpen(false);
                    }}
                    className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left font-medium text-on-surface hover:bg-surface-container-low transition"
                  >
                    <User size={16} className="text-on-surface-variant" />
                    <span>Profile</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setActiveModal('settings');
                      setIsProfileMenuOpen(false);
                    }}
                    className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left font-medium text-on-surface hover:bg-surface-container-low transition"
                  >
                    <Settings size={16} className="text-on-surface-variant" />
                    <span>Settings</span>
                  </button>
                </div>

                <div className="my-1.5 h-px bg-outline-variant/20" />

                <div className="space-y-0.5 text-sm">
                  <button
                    type="button"
                    onClick={() => {
                      setActiveModal('help');
                      setIsProfileMenuOpen(false);
                    }}
                    className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left font-medium text-on-surface hover:bg-surface-container-low transition"
                  >
                    <div className="flex items-center gap-3">
                      <HelpCircle size={16} className="text-on-surface-variant" />
                      <span>Help</span>
                    </div>
                    <ChevronRight size={16} className="text-on-surface-variant" />
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setIsProfileMenuOpen(false);
                      handleLogout();
                    }}
                    className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left font-medium text-error hover:bg-error-container/20 transition"
                  >
                    <LogOut size={16} />
                    <span>Log out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1">
        {activeTab === 'chat' ? (
          <ChatPage
            embedded
            authToken={authToken}
            user={currentUser}
            onLogout={handleLogout}
            onGenerateLegalNotice={generateNoticeFromChat}
            onUsageBump={bumpUsage}
          />
        ) : activeTab === 'legal-notice' ? (
          <LegalNoticeGenerator
            draft={noticeDraft}
            initialCaseDetails={initialCaseDetails}
            isGenerating={isGeneratingNotice}
            error={noticeError}
            userName={currentUser.full_name}
            onLogout={handleLogout}
            onCreateNew={createNewNotice}
            history={noticeHistory}
            activeHistoryId={activeNoticeHistoryId}
            onSelectHistory={selectNoticeHistory}
            onGenerate={generateNotice}
          />
        ) : (
          <DocumentGenerator
            draft={documentDraft}
            isGenerating={isGeneratingDocument}
            error={documentError}
            userName={currentUser.full_name}
            onLogout={handleLogout}
            onCreateNew={createNewDocument}
            history={documentHistory}
            activeHistoryId={activeDocumentHistoryId}
            onSelectHistory={selectDocumentHistory}
            onGenerate={generateDocument}
          />
        )}
      </div>

      {/* Settings & Profile Modals */}
      {activeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="relative w-full max-w-md rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-6 shadow-2xl text-on-surface space-y-4">
            <div className="flex items-center justify-between border-b border-outline-variant/20 pb-3">
              <div className="flex items-center gap-2 font-semibold text-lg">
                {activeModal === 'profile' && <User className="text-primary" size={20} />}
                {activeModal === 'settings' && <Settings className="text-primary" size={20} />}
                {activeModal === 'personalization' && <Sliders className="text-primary" size={20} />}
                {activeModal === 'upgrade' && <Sparkles className="text-amber-400" size={20} />}
                {activeModal === 'help' && <HelpCircle className="text-primary" size={20} />}
                <span className="capitalize">{activeModal === 'upgrade' ? 'Upgrade Plan' : activeModal}</span>
              </div>
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="flex h-8 w-8 items-center justify-center rounded-xl hover:bg-surface-container-high text-on-surface-variant transition"
              >
                <X size={18} />
              </button>
            </div>

            {activeModal === 'profile' && (
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-3 p-3 rounded-xl bg-surface-container-low">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-purple-600 text-lg font-bold text-white">
                    {getUserInitials(currentUser.full_name, currentUser.email)}
                  </div>
                  <div>
                    <div className="font-semibold text-base">{currentUser.full_name}</div>
                    <div className="text-xs text-on-surface-variant">{currentUser.email}</div>
                  </div>
                </div>
                <div className="space-y-2 pt-2">
                  <div className="flex justify-between py-1 border-b border-outline-variant/10 text-xs">
                    <span className="text-on-surface-variant">User ID</span>
                    <span className="font-mono text-on-surface truncate max-w-[200px]">{currentUser.user_id}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-outline-variant/10 text-xs">
                    <span className="text-on-surface-variant">Current Plan</span>
                    <span className="font-semibold text-primary">Free Plan</span>
                  </div>
                  <div className="flex justify-between py-1 text-xs">
                    <span className="text-on-surface-variant">Daily Tokens</span>
                    <span className="text-on-surface">100,000 / day</span>
                  </div>
                </div>
              </div>
            )}

            {activeModal === 'settings' && (
              <div className="space-y-4 text-sm">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-on-surface-variant">AI Intelligence Model</label>
                  <div className="p-2.5 rounded-xl border border-outline-variant/30 bg-surface-container-low text-xs font-medium">
                    Amazon Bedrock (Mistral Large 3 Legal Model)
                  </div>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-on-surface-variant">Legal Jurisdiction</label>
                  <div className="p-2.5 rounded-xl border border-outline-variant/30 bg-surface-container-low text-xs font-medium">
                    Republic of India (BNS, BNSS, BSA & Statutory Frameworks)
                  </div>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-on-surface-variant">Interface Theme</label>
                  <div className="p-2.5 rounded-xl border border-outline-variant/30 bg-surface-container-low text-xs font-medium">
                    Dark Mode (Active)
                  </div>
                </div>
              </div>
            )}

            {activeModal === 'personalization' && (
              <div className="space-y-3 text-sm">
                <p className="text-xs text-on-surface-variant">Customize how the AI drafts legal notices and answers legal queries.</p>
                <div className="p-3 rounded-xl border border-outline-variant/20 bg-surface-container-low space-y-2">
                  <div className="font-semibold text-xs text-primary">Legal Drafting Tone</div>
                  <div className="text-xs text-on-surface">Senior Indian Advocate Style (Formal, clean, numbered paragraphs, no AI disclaimers)</div>
                </div>
                <div className="p-3 rounded-xl border border-outline-variant/20 bg-surface-container-low space-y-2">
                  <div className="font-semibold text-xs text-primary">RAG Legal Indexing</div>
                  <div className="text-xs text-on-surface">Enabled (Auto-retrieves Indian Acts & Sections)</div>
                </div>
              </div>
            )}

            {activeModal === 'upgrade' && (
              <div className="space-y-4 text-sm">
                <div className="p-4 rounded-xl bg-gradient-to-br from-purple-900/30 to-indigo-900/30 border border-purple-500/30 text-center space-y-2">
                  <div className="font-bold text-base text-amber-400">LAW LLM Pro Tier</div>
                  <div className="text-xs text-on-surface-variant">Unlimited daily tokens, priority Bedrock response speeds, and advanced document drafting.</div>
                </div>
                <div className="space-y-2 text-xs">
                  <div className="flex items-center gap-2"><Check size={14} className="text-primary" /> Unlimited daily token usage</div>
                  <div className="flex items-center gap-2"><Check size={14} className="text-primary" /> Multi-lawyer team collaboration</div>
                  <div className="flex items-center gap-2"><Check size={14} className="text-primary" /> Custom advocate letterhead templates</div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    alert('You are currently using the Free Plan with 100,000 daily tokens.');
                    setActiveModal(null);
                  }}
                  className="primary-button w-full justify-center"
                >
                  Upgrade to Pro
                </button>
              </div>
            )}

            {activeModal === 'help' && (
              <div className="space-y-3 text-sm">
                <p className="text-xs text-on-surface-variant">Legal AI Chat Assistant documentation & support.</p>
                <div className="space-y-2 text-xs">
                  <div className="p-2.5 rounded-xl border border-outline-variant/20 bg-surface-container-low">
                    <div className="font-semibold text-on-surface">Legal Notice Generator</div>
                    <div className="text-on-surface-variant text-[11px] mt-0.5">Enter client, advocate, recipient, and case facts to generate a ready-to-dispatch notice. Export to TXT or DOC.</div>
                  </div>
                  <div className="p-2.5 rounded-xl border border-outline-variant/20 bg-surface-container-low">
                    <div className="font-semibold text-on-surface">Document Generator</div>
                    <div className="text-on-surface-variant text-[11px] mt-0.5">Select a document skill (Lease, Agreement, Petition, etc.) to generate structured drafts.</div>
                  </div>
                </div>
              </div>
            )}

            <div className="pt-2">
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="neutral-button w-full justify-center text-xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
