import React, { useCallback, useEffect, useState } from 'react';
import { Bell, BriefcaseBusiness, ChevronDown, Command, FileStack, LayoutDashboard, LogOut, Search, Settings, Users } from 'lucide-react';
import { betaConfig } from './core/betaConfig';
import {
  clearSession,
  createMatter,
  fetchMatterOverview,
  fetchV1Status,
  getStoredToken,
  getStoredUser,
  listMatters,
  Matter,
  MatterCreateInput,
  MatterOverview,
  runMatterAgent,
  uploadMatterDocument,
  V1AuthResult,
  V1User,
} from './core/api';
import { LoginPage } from './features/auth/LoginPage';
import { CaseAgentPanel } from './features/case-agent/CaseAgentPanel';
import { CreateMatterDialog } from './features/matters/CreateMatterDialog';
import { MatterTab, MatterWorkspace } from './features/matters/MatterWorkspace';
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
  const [matters, setMatters] = useState<Matter[]>([]);
  const [selectedMatterId, setSelectedMatterId] = useState<string | null>(null);
  const [overview, setOverview] = useState<MatterOverview | null>(null);
  const [activeTab, setActiveTab] = useState<MatterTab>('Overview');
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [isWorkspaceLoading, setIsWorkspaceLoading] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

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

  const openMatter = useCallback(async (matterId: string) => {
    setSelectedMatterId(matterId);
    setIsWorkspaceLoading(true);
    setWorkspaceError(null);
    try {
      setOverview(await fetchMatterOverview(matterId));
      setActiveTab('Overview');
    } catch (error) {
      setWorkspaceError(error instanceof Error ? error.message : 'Unable to load the matter.');
    } finally {
      setIsWorkspaceLoading(false);
    }
  }, []);

  useEffect(() => {
    if (appState !== 'workspace') return;
    let cancelled = false;
    setIsWorkspaceLoading(true);
    void listMatters().then(async (items) => {
      if (cancelled) return;
      setMatters(items);
      if (items.length) await openMatter(items[0].matter_id);
    }).catch((error) => {
      if (!cancelled) setWorkspaceError(error instanceof Error ? error.message : 'Unable to load matters.');
    }).finally(() => {
      if (!cancelled) setIsWorkspaceLoading(false);
    });
    return () => { cancelled = true; };
  }, [appState, openMatter]);

  const handleCreateMatter = async (input: MatterCreateInput, file?: File | null) => {
    setIsCreating(true);
    setWorkspaceError(null);
    try {
      const matter = await createMatter(input);
      if (file) {
        try {
          await uploadMatterDocument(matter.matter_id, file);
        } catch (uploadErr) {
          console.warn('Could not auto-attach uploaded document to matter workspace:', uploadErr);
        }
      }
      setMatters((current) => [matter, ...current]);
      setIsCreateOpen(false);
      await openMatter(matter.matter_id);
    } catch (error) {
      setWorkspaceError(error instanceof Error ? error.message : 'Unable to create the matter.');
    } finally {
      setIsCreating(false);
    }
  };


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
          <button className="new-matter" onClick={() => setIsCreateOpen(true)}>+ New matter</button>
          <nav>
            {navigation.map(({ label, icon: Icon, active }) => (
              <button className={active ? 'active' : ''} disabled={!active} key={label}>
                <Icon size={17} />{label}
              </button>
            ))}
            {matters.map((matter) => (
              <button
                className={`matter-nav-item ${selectedMatterId === matter.matter_id ? 'active' : ''}`}
                key={matter.matter_id}
                onClick={() => void openMatter(matter.matter_id)}
                title={matter.title}
              >
                <BriefcaseBusiness size={15} />{matter.title}
              </button>
            ))}
          </nav>
          <div className="sidebar-footer">
            <button disabled><Settings size={17} /> Settings</button>
            <div className="build-label">{betaConfig.releaseStage} build</div>
          </div>
        </aside>

        <div className="workspace-grid">
          <MatterWorkspace
            overview={overview}
            activeTab={activeTab}
            isLoading={isWorkspaceLoading}
            error={workspaceError}
            onTabChange={setActiveTab}
            onCreateMatter={() => setIsCreateOpen(true)}
          />
          <CaseAgentPanel
            matter={overview?.matter_details ?? null}
            overview={overview}
            onRun={async (command) => {
              if (!selectedMatterId) throw new Error('Select a matter first.');
              const result = await runMatterAgent(selectedMatterId, command);
              if (result.status === 'failed') throw new Error(result.error_text || 'The Case Agent failed.');
              return result.output_text || 'The command completed without output.';
            }}
            onRefreshOverview={() => selectedMatterId && openMatter(selectedMatterId)}
          />
          <SourcePanel />
        </div>

      </div>
      {isCreateOpen && (
        <CreateMatterDialog
          isSaving={isCreating}
          error={workspaceError}
          onClose={() => !isCreating && setIsCreateOpen(false)}
          onCreate={handleCreateMatter}
        />
      )}
    </div>
  );
}
