const API_BASE = import.meta.env.VITE_V1_API_BASE || 'http://localhost:9001/v1';
const ACCESS_KEY = 'legalai_v1_access';

export class V1Api {
  private accessToken: string | null = sessionStorage.getItem(ACCESS_KEY);

  async launch(primaryAccessToken: string) {
    const response = await fetch(`${API_BASE}/launch`, { method: 'POST', headers: { Authorization: `Bearer ${primaryAccessToken}` } });
    if (!response.ok) throw new Error('Unable to launch V1.');
    const { launch_token } = await response.json();
    return this.acceptLaunch(launch_token);
  }

  async acceptLaunch(launch_token: string) {
    const exchanged = await fetch(`${API_BASE}/auth/exchange`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ launch_token }) });
    if (!exchanged.ok) throw new Error('V1 session could not be authenticated.');
    const { access_token } = await exchanged.json();
    this.accessToken = access_token;
    sessionStorage.setItem(ACCESS_KEY, access_token);
  }

  get authenticated() { return Boolean(this.accessToken); }

  clearSession() { this.accessToken = null; sessionStorage.removeItem(ACCESS_KEY); }

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, { ...init, headers: { ...init.headers, ...(this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {}) } });
    if (response.status === 401) { this.clearSession(); throw new Error('Your V1 session expired. Please launch V1 again.'); }
    if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'V1 request failed.');
    return response.json();
  }
}

export const v1Api = new V1Api();
