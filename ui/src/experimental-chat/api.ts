const DEFAULT_CHAT_URL = '/tllac-api/chat';

export class ApiResponseError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: unknown,
    message: string,
  ) {
    super(message);
    this.name = 'ApiResponseError';
  }
}

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

export function getApiCandidates(): string[] {
  const configuredChatUrl = getConfiguredChatUrl();
  const candidateUrls: string[] = [];

  if (configuredChatUrl && !shouldPreferProxy(configuredChatUrl)) {
    candidateUrls.push(configuredChatUrl);
  }
  if (!candidateUrls.includes(DEFAULT_CHAT_URL)) {
    candidateUrls.push(DEFAULT_CHAT_URL);
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
        let responseDetail: unknown = null;
        try {
          const errorData = await response.json();
          responseDetail = errorData?.detail;
          if (typeof errorData?.detail === 'string') {
            detail = errorData.detail;
          }
        } catch {
          // Ignore error-body parsing failures.
        }
        throw new ApiResponseError(response.status, responseDetail, detail);
      }
      return (await response.json()) as T;
    } catch (error) {
      // An HTTP response proves that the backend was reached. Retrying a write
      // against another host can duplicate it and hides the original error.
      if (error instanceof ApiResponseError) {
        throw error;
      }
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
        throw new ApiResponseError(
          response.status,
          null,
          `Request failed with status ${response.status}`,
        );
      }
      const disposition = response.headers.get('content-disposition') || '';
      const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
      return {
        blob: await response.blob(),
        filename: filenameMatch?.[1] ?? null,
      };
    } catch (error) {
      if (error instanceof ApiResponseError) {
        throw error;
      }
      lastError = error;
    }
  }

  throw lastError instanceof Error ? lastError : new Error('Backend unavailable.');
}
