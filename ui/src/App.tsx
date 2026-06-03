import React, { useEffect, useState } from 'react';
import { FilePenLine, FileText, MessageSquare } from 'lucide-react';
import { AuthFormValue, AuthPage } from './auth/AuthPage';
import { DocumentDraft, DocumentGenerator, type DocumentGeneratorInput } from './DocumentGenerator';
import { getDocumentSkillByType } from './documentSkills';
import ChatPage from './experimental-chat/ChatPage';
import { requestWithFallback } from './experimental-chat/api';
import { LegalNoticeDraft, LegalNoticeGenerator } from './LegalNoticeGenerator';

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
): Promise<string> {
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
      return notice;
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError instanceof Error ? lastError : new Error('Unable to reach legal notice generator.');
}

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('chat');
  const [noticeDraft, setNoticeDraft] = useState<LegalNoticeDraft | null>(null);
  const [documentDraft, setDocumentDraft] = useState<DocumentDraft | null>(null);
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
      const notice = await requestLegalNotice(authToken, input);
      setNoticeDraft({ ...input, notice });
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
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : 'Unable to prepare document draft.');
    } finally {
      setIsGeneratingDocument(false);
    }
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
        <div className="flex items-center justify-between px-4 md:px-6">
          <div className="hidden text-sm text-on-surface-variant md:block">{currentUser.email}</div>
          <div className="ml-auto flex items-center justify-end">
            <button type="button" onClick={() => setActiveTab('chat')} className={tabClass('chat')}>
              <MessageSquare size={17} />
              Legal Chat
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('legal-notice')}
              className={tabClass('legal-notice')}
            >
              <FileText size={17} />
              Legal Notice Generator
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('document-generator')}
              className={tabClass('document-generator')}
            >
              <FilePenLine size={17} />
              Document Generator
            </button>
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
          />
        ) : activeTab === 'legal-notice' ? (
          <LegalNoticeGenerator
            draft={noticeDraft}
            initialCaseDetails={initialCaseDetails}
            isGenerating={isGeneratingNotice}
            error={noticeError}
            onGenerate={generateNotice}
          />
        ) : (
          <DocumentGenerator
            draft={documentDraft}
            isGenerating={isGeneratingDocument}
            error={documentError}
            onGenerate={generateDocument}
          />
        )}
      </div>
    </div>
  );
};

export default App;
