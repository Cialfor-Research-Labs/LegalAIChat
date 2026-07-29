import React, { useCallback, useEffect, useState } from 'react';
import { Bell, BriefcaseBusiness, ChevronDown, Command, FileStack, LayoutDashboard, LogOut, Search, Settings, Users } from 'lucide-react';
import { betaConfig } from './core/betaConfig';
import { clearSession, fetchV1Status, getStoredToken, getStoredUser, V1AuthResult, V1User } from './core/api';
import { LoginPage } from './features/auth/LoginPage';
import { CaseAgentPanel } from './features/case-agent/CaseAgentPanel';
import { MatterWorkspace } from './features/matters/MatterWorkspace';
import { SourcePanel } from './features/research/SourcePanel';

const navigation = [
  { label: 'Dashboard', icon: LayoutDashboard },
  { label: 'Matters', icon: BriefcaseBusiness, active: true },
  { label: 'Documents', icon: FileStack },
  { label: 'Review queue', icon: Command },
  { label: 'Team', icon: Users },
];

type AppState = 'checking' | 'disabled' | 'login' | 'workspace';

export function App() {
  const [appState, setAppState]   = useState<AppState>('checking');
  const [user, setUser]           = useState<V1User | null>(null);

  // ── Bootstrap: check feature flag + restore session ──────────────────────
  useEffect(() => {
    async function bootstrap() {
      try {
        const status = await fetchV1Status();
        if (!status.v1_enabled) { setAppState('disabled'); return; }
      } catch {
        // If the backend is unreachable, proceed to login; it will show a
        // clear error when the user actually tries to sign in.
      }

      // Restore persisted session
      const token = getStoredToken();
      const stored = getStoredUser();
      if (token && stored) {
        setUser(stored);
        setAppState('workspace');
      } else {
        setAppState('login');
      }
    }
    bootstrap();
  }, []);

  const handleAuthenticated = useCallback((result: V1AuthResult) => {
    setUser(result.user);
    setAppState('workspace');
  }, []);

  const handleLogout = useCallback(() => {
    clearSession();
    setUser(null);
    setAppState('login');
  }, []);

  // ── Render states ─────────────────────────────────────────────────────────
  if (appState === 'checking') {
    return (
      <div className="boot-screen">
        <div className="login-brand-mark" style={{ margin: '0 auto 16px' }}>V</div>
        <p style={{ color: 'var(--muted)', fontSize: 12 }}>Loading…</p>
      </div>
    );
  }

  if (appState === 'disabled') {
    return (
      <div className="boot-screen">
        <div className="login-brand-mark" style={{ margin: '0 auto 16px' }}>V</div>
        <h2 style={{ fontFamily: 'Georgia, serif', marginBottom: 8 }}>V1 Beta is currently disabled</h2>
        <p style={{ color: 'var(--muted)', fontSize: 12, maxWidth: 320, textAlign: 'center' }}>
          This workspace has been turned off by the administrator. Check back later.
        </p>
      </div>
    );
  }

  if (appState === 'login') {
    return <LoginPage onAuthenticated={handleAuthenticated} />;
  }

  // ── Workspace ─────────────────────────────────────────────────────────────
  const initials = user
    ? user.full_name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()
    : 'VA';

  return (
    <div className="beta-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">V</div>
          <div>
            <strong>VIDHI AI</strong>
            <span>{betaConfig.label}</span>
          </div>
        </div>
        <div className="isolation-notice">{betaConfig.dataMode}</div>
        <div className="topbar-actions">
          <button aria-label="Search" disabled><Search size={18} /></button>
          <button aria-label="Notifications" disabled><Bell size={18} /></button>
          <div className="profile" title={user?.full_name}>{initials}</div>
          <ChevronDown size={15} />
          <button
            aria-label="Sign out"
            onClick={handleLogout}
            title="Sign out"
            style={{ marginLeft: 4 }}
          >
            <LogOut size={17} />
          </button>
        </div>
      </header>

      <div className="app-frame">
        <aside className="primary-sidebar">
          <button className="new-matter" disabled>+ New matter</button>
          <nav>
            {navigation.map(({ label, icon: Icon, active }) => (
              <button className={active ? 'active' : ''} disabled key={label}>
                <Icon size={17} />{label}
              </button>
            ))}
          </nav>
          <div className="sidebar-footer">
            <button disabled><Settings size={17} /> Settings</button>
            <div className="build-label">{betaConfig.releaseStage} build</div>
          </div>
        </aside>

        <div className="workspace-grid">
          <MatterWorkspace />
          <CaseAgentPanel />
          <SourcePanel />
        </div>
      </div>
    </div>
  );
}
