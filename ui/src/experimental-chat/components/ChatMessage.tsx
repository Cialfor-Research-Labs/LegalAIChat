import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FileText, User, Bot } from 'lucide-react';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  legalNoticePrompt?: string;
  animateOnMount?: boolean;
}

interface ChatMessageProps {
  message: Message;
  onGenerateLegalNotice?: (caseDetails: string) => void;
}

const typedMessageIds = new Set<string>();

function isTableLikeLine(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed.includes('|')) {
    return false;
  }
  const cellCount = trimmed.split('|').filter((part) => part.trim().length > 0).length;
  return cellCount >= 2;
}

function isSeparatorLikeLine(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed) {
    return false;
  }
  const withoutPipes = trimmed.replace(/\|/g, '').trim();
  return withoutPipes.length > 0 && /^[-:\s]+$/.test(withoutPipes);
}

function toCells(row: string): string[] {
  return row
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim())
    .filter((cell) => cell.length > 0);
}

function formatMarkdownRow(cells: string[]): string {
  return `| ${cells.join(' | ')} |`;
}

function rebuildMalformedTableBlock(block: string): string {
  if (!block.includes('|')) {
    return block;
  }

  const flattened = block
    .replace(/\r/g, '')
    .replace(/:\s+\|/g, ':\n|')
    .replace(/\s*\|\|\s*/g, '\n|')
    .replace(/\|\s+(?=\|)/g, '|\n|');

  const rawLines = flattened
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  const tableLines = rawLines.filter((line) => isTableLikeLine(line) || isSeparatorLikeLine(line));
  if (tableLines.length < 2) {
    return block;
  }

  const headerCells = toCells(tableLines[0]);
  if (headerCells.length < 2) {
    return block;
  }

  const columnCount = headerCells.length;
  const normalizedRows: string[] = [
    formatMarkdownRow(headerCells),
    formatMarkdownRow(Array.from({ length: columnCount }, () => '---')),
  ];

  for (const line of tableLines.slice(1)) {
    if (isSeparatorLikeLine(line)) {
      continue;
    }

    const cells = toCells(line);
    if (cells.length === 0) {
      continue;
    }
    if (cells.length !== columnCount) {
      continue;
    }

    normalizedRows.push(formatMarkdownRow(cells));
  }

  return normalizedRows.length >= 3 ? normalizedRows.join('\n') : block;
}

function normalizeMarkdownTables(content: string): string {
  if (!content.includes('|')) {
    return content;
  }

  const blocks = content.split(/\n\s*\n/);
  return blocks
    .map((block) => rebuildMalformedTableBlock(block))
    .join('\n\n');
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, onGenerateLegalNotice }) => {
  const isUser = message.role === 'user';
  const shouldAnimate = !isUser && message.animateOnMount !== false && !typedMessageIds.has(message.id);
  const [visibleContent, setVisibleContent] = useState(shouldAnimate ? '' : message.content);
  const isTyping = !isUser && visibleContent.length < message.content.length;
  const markdownContent = normalizeMarkdownTables(visibleContent);

  useEffect(() => {
    if (isUser) {
      setVisibleContent(message.content);
      return;
    }

    if (message.animateOnMount === false) {
      typedMessageIds.add(message.id);
      setVisibleContent(message.content);
      return;
    }

    if (typedMessageIds.has(message.id)) {
      setVisibleContent(message.content);
      return;
    }

    setVisibleContent('');
    let index = 0;
    const chunkSize = message.content.length > 1800 ? 12 : message.content.length > 800 ? 8 : 4;
    const interval = window.setInterval(() => {
      index = Math.min(index + chunkSize, message.content.length);
      setVisibleContent(message.content.slice(0, index));

      if (index >= message.content.length) {
        typedMessageIds.add(message.id);
        window.clearInterval(interval);
      }
    }, 18);

    return () => window.clearInterval(interval);
  }, [isUser, message.animateOnMount, message.content, message.id]);

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      <div className={`flex max-w-[85%] md:max-w-[75%] ${isUser ? 'flex-row-reverse' : 'flex-row'} gap-3`}>
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${isUser ? 'bg-primary text-on-primary' : 'bg-secondary text-on-secondary'}`}>
          {isUser ? <User size={18} /> : <Bot size={18} />}
        </div>
        <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
          <div className="text-xs text-on-surface-variant mb-1 mx-1 font-medium">
            {isUser ? 'You' : 'AI Assistant'}
          </div>
          <div 
            className={`p-4 rounded-2xl text-sm md:text-base leading-relaxed ${
              isUser 
                ? 'bg-primary text-on-primary rounded-tr-sm' 
                : 'bg-surface-container-low text-on-surface rounded-tl-sm border border-outline-variant/20 shadow-sm'
            }`}
          >
            {isUser ? (
              <div className="whitespace-pre-wrap">{message.content}</div>
            ) : (
              <div className="chat-markdown prose prose-sm dark:prose-invert prose-p:leading-relaxed prose-pre:bg-surface-container prose-pre:border prose-pre:border-outline-variant/30 max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    table: ({ children }) => (
                      <div className="chat-markdown-table-wrap">
                        <table>{children}</table>
                      </div>
                    ),
                  }}
                >
                  {markdownContent}
                </ReactMarkdown>
                {isTyping && (
                  <span className="typing-caret" aria-hidden="true" />
                )}
              </div>
            )}
            {!isUser && !isTyping && message.legalNoticePrompt && onGenerateLegalNotice && (
              <button
                type="button"
                onClick={() => onGenerateLegalNotice(message.legalNoticePrompt || '')}
                className="mt-4 inline-flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-sm font-semibold text-primary transition hover:bg-primary/15"
              >
                <FileText size={16} />
                Generate Legal Notice
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
