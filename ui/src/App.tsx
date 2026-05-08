import React, { useState } from 'react';
import { FileText, MessageSquare } from 'lucide-react';
import ChatPage from './experimental-chat/ChatPage';
import { LegalNoticeDraft, LegalNoticeGenerator } from './LegalNoticeGenerator';

type ActiveTab = 'chat' | 'legal-notice';

const LEGAL_NOTICE_PROXY_URL = '/tllac-api/legal-notice/generate';
const LOCAL_LEGAL_NOTICE_URL = 'http://127.0.0.1:9001/legal-notice/generate';

function getHostBasedLegalNoticeUrl(): string {
  const { protocol, hostname } = window.location;
  const resolvedProtocol = protocol === 'https:' ? 'https:' : 'http:';
  const resolvedHostname = hostname || '127.0.0.1';
  return `${resolvedProtocol}//${resolvedHostname}:9001/legal-notice/generate`;
}

async function requestLegalNotice(input: Omit<LegalNoticeDraft, 'notice'>): Promise<string> {
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
        headers: { 'Content-Type': 'application/json' },
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
  const [initialCaseDetails, setInitialCaseDetails] = useState('');
  const [isGeneratingNotice, setIsGeneratingNotice] = useState(false);
  const [noticeError, setNoticeError] = useState<string | null>(null);

  const generateNotice = async (input: Omit<LegalNoticeDraft, 'notice'>) => {
    setActiveTab('legal-notice');
    setInitialCaseDetails(input.caseDetails);
    setIsGeneratingNotice(true);
    setNoticeError(null);

    try {
      const notice = await requestLegalNotice(input);
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
      relevantInfo: 'Generated from the legal chat conversation. Fill missing client, lawyer, recipient, address, date, amount, and document details before dispatch.',
    });
  };

  const tabClass = (tab: ActiveTab) =>
    [
      'inline-flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-semibold transition',
      activeTab === tab
        ? 'border-primary text-primary'
        : 'border-transparent text-on-surface-variant hover:text-on-surface',
    ].join(' ');

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-surface font-body text-on-surface" data-theme="dark">
      <div className="border-b border-outline-variant/20 bg-surface-container">
        <div className="flex items-center px-4 md:px-6">
          <button type="button" onClick={() => setActiveTab('chat')} className={tabClass('chat')}>
            <MessageSquare size={17} />
            Legal Chat
          </button>
          <button type="button" onClick={() => setActiveTab('legal-notice')} className={tabClass('legal-notice')}>
            <FileText size={17} />
            Legal Notice Generator
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1">
        {activeTab === 'chat' ? (
          <ChatPage embedded onGenerateLegalNotice={generateNoticeFromChat} />
        ) : (
          <LegalNoticeGenerator
            draft={noticeDraft}
            initialCaseDetails={initialCaseDetails}
            isGenerating={isGeneratingNotice}
            error={noticeError}
            onGenerate={generateNotice}
          />
        )}
      </div>
    </div>
  );
};

export default App;
