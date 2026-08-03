/**
 * Typed API client for V1 Beta.
 * All requests go to the shared TLLAC backend (port 9001).
 * Auth token is read from localStorage key "v1_access_token".
 */

import { betaConfig } from './betaConfig';

const BASE = betaConfig.apiBase;
const TOKEN_KEY = 'v1_access_token';
const USER_KEY  = 'v1_user';

// ── Token storage ─────────────────────────────────────────────────────────────

export function saveSession(token: string, user: V1User): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): V1User | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw) as V1User; } catch { return null; }
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface V1User {
  user_id: string;
  email: string;
  full_name: string;
}

export interface V1AuthResult {
  access_token: string;
  token_type: string;
  user: V1User;
}

export interface V1StatusResult {
  v1_enabled: boolean;
  version: string;
}

// ── Fetch helpers ─────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(init.headers ?? {}),
    },
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === 'string') detail = body.detail;
      else if (typeof body?.detail === 'object') detail = JSON.stringify(body.detail);
    } catch { /* ignore parse errors */ }
    throw new Error(detail);
  }

  return res.json() as Promise<T>;
}

export interface Matter {
  matter_id: string;
  title: string;
  description: string;
  case_number: string | null;
  court: string | null;
  jurisdiction: string | null;
  stage: string | null;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface MatterOverview {
  matter_details: Matter;
  parties: Record<string, unknown>[];
  counsel: Record<string, unknown>[];
  hearings: Record<string, unknown>[];
  open_tasks: Record<string, unknown>[];
  notes: Record<string, unknown>[];
  timeline_events: Record<string, unknown>[];
  documents: Record<string, unknown>[];
  research: Record<string, unknown>[];
  drafts: Record<string, unknown>[];
}

export interface MatterCreateInput {
  title: string;
  description: string;
  case_number?: string;
  court?: string;
  jurisdiction?: string;
  stage?: string;
}

export interface AgentRunResult {
  agent_run_id: string;
  command: string;
  status: string;
  output_text: string | null;
  error_text: string | null;
}

export async function listMatters(): Promise<Matter[]> {
  const result = await apiFetch<{ matters: Matter[] }>('/v1/matters');
  return result.matters;
}

export function createMatter(input: MatterCreateInput): Promise<Matter> {
  return apiFetch<Matter>('/v1/matters', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function fetchMatterOverview(matterId: string): Promise<MatterOverview> {
  return apiFetch<MatterOverview>(`/v1/matters/${matterId}/overview`);
}

export function runMatterAgent(matterId: string, commandText: string): Promise<AgentRunResult> {
  return apiFetch<AgentRunResult>(`/v1/matters/${matterId}/agent/run`, {
    method: 'POST',
    body: JSON.stringify({ command_text: commandText, conversation_history: [] }),
  });
}

function authHeaders(): Record<string, string> {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── Auth API calls ────────────────────────────────────────────────────────────

/** Check whether the V1 feature flag is enabled on the backend. */
export async function fetchV1Status(): Promise<V1StatusResult> {
  return apiFetch<V1StatusResult>('/v1/auth/status');
}

/** Direct login with email + password → access token. */
export async function loginV1(email: string, password: string): Promise<V1AuthResult> {
  return apiFetch<V1AuthResult>('/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

/**
 * Exchange a launch token (from the main Vidhi AI app SSO flow) for a
 * full V1 session token.  The launch token is read from the URL hash
 * or a query parameter before calling this.
 */
export async function exchangeLaunchToken(launchToken: string): Promise<V1AuthResult> {
  return apiFetch<V1AuthResult>('/v1/auth/exchange', {
    method: 'POST',
    body: JSON.stringify({ launch_token: launchToken }),
  });
}

/**
 * Called from the existing Vidhi AI app to obtain a short-lived launch
 * token for the logged-in user.  Requires an existing Bearer token.
 */
export async function fetchLaunchToken(): Promise<{ launch_token: string; expires_in_seconds: number }> {
  return apiFetch('/v1/auth/launch-token', { headers: authHeaders() });
}
