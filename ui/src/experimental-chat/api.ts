const DEFAULT_CHAT_URL = '/tllac-api/chat';
const LOCAL_CHAT_URL = 'http://127.0.0.1:9001/chat';

function normalizeChatUrl(url: string): string {
  const trimmed = url.trim().replace(/\/$/, '');
  return trimmed.endsWith('/chat') ? trimmed : `${trimmed}/chat`;
}

function isLocalhostUrl(url: string): boolean {
  return /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?(\/|$)/i.test(url);
}

function shouldPreferProxy(configuredUrl: string): boolean {
  const hostname = window.location.hostname;
  const isLocalBrowser = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '';
  return isLocalhostUrl(configuredUrl) && !isLocalBrowser;
}

export function getConfiguredChatUrl(): string | null {
  const configured = import.meta.env.VITE_TLLAC_API_URL?.trim();
  if (!configured) {
    return null;
  }
  return normalizeChatUrl(configured);
}

export function getHostBasedChatUrl(): string {
  const { protocol, hostname } = window.location;
  const resolvedProtocol = protocol === 'https:' ? 'https:' : 'http:';
  const resolvedHostname = hostname || '127.0.0.1';
  return `${resolvedProtocol}//${resolvedHostname}:9001/chat`;
}

export function getApiCandidates(): string[] {
  const configuredChatUrl = getConfiguredChatUrl();
  const hostBasedChatUrl = getHostBasedChatUrl();
  const candidateUrls: string[] = [];

  if (configuredChatUrl && !shouldPreferProxy(configuredChatUrl)) {
    candidateUrls.push(configuredChatUrl);
  }
  if (!candidateUrls.includes(DEFAULT_CHAT_URL)) {
    candidateUrls.push(DEFAULT_CHAT_URL);
  }
  if (!candidateUrls.includes(hostBasedChatUrl)) {
    candidateUrls.push(hostBasedChatUrl);
  }
  if (!candidateUrls.includes(LOCAL_CHAT_URL)) {
    candidateUrls.push(LOCAL_CHAT_URL);
  }
  if (configuredChatUrl && !candidateUrls.includes(configuredChatUrl)) {
    candidateUrls.push(configuredChatUrl);
  }

  return candidateUrls;
}

export function toApiBase(chatUrl: string): string {
  return chatUrl.endsWith('/chat') ? chatUrl.slice(0, -5) : chatUrl;
}

export async function requestWithFallback<T>(
  path: string,
  initFactory: () => RequestInit,
): Promise<T> {
  let lastError: unknown = null;

  for (const chatUrl of getApiCandidates()) {
    const url = `${toApiBase(chatUrl)}${path}`;
    try {
      const response = await fetch(url, initFactory());
      if (!response.ok) {
        let detail = `Request failed with status ${response.status}`;
        try {
          const errorData = await response.json();
          if (typeof errorData?.detail === 'string') {
            detail = errorData.detail;
          }
        } catch {
          // Ignore error-body parsing failures.
        }
        throw new Error(detail);
      }
      return (await response.json()) as T;
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError instanceof Error ? lastError : new Error('Backend unavailable.');
}

export async function requestBlobWithFallback(
  path: string,
  initFactory: () => RequestInit,
): Promise<{ blob: Blob; filename: string | null }> {
  let lastError: unknown = null;

  for (const chatUrl of getApiCandidates()) {
    const url = `${toApiBase(chatUrl)}${path}`;
    try {
      const response = await fetch(url, initFactory());
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }
      const disposition = response.headers.get('content-disposition') || '';
      const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
      return {
        blob: await response.blob(),
        filename: filenameMatch?.[1] ?? null,
      };
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError instanceof Error ? lastError : new Error('Backend unavailable.');
}
