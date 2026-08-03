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

type WorkspaceSection = 'dashboard' | 'matters' | 'documents' | 'review-queue' | 'team';

const navigation = [
  { label: 'Dashboard', icon: LayoutDashboard, section: 'dashboard' as const },
  { label: 'Matters', icon: BriefcaseBusiness, section: 'matters' as const },
  { label: 'Documents', icon: FileStack, section: 'documents' as const },
  { label: 'Review queue', icon: Command, section: 'review-queue' as const },
  { label: 'Team', icon: Users, section: 'team' as const },
];

type AppState = 'checking' | 'disabled' | 'login' | 'workspace';

export function App() {
  const [appState, setAppState] = useState<AppState>('checking');
  const [user, setUser] = useState<V1User | null>(null);
  const [matters, setMatters] = useState<Matter[]>([]);
  const [selectedMatterId, setSelectedMatterId] = useState<string | null>(null);
  const [overview, setOverview] = useState<MatterOverview | null>(null);
  const [activeSection, setActiveSection] = useState<WorkspaceSection>('matters');
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
        // If backend is unreachable, proceed to login
      }

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
    setActiveSection('matters');
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

  const handleNavigate = useCallback((section: WorkspaceSection) => {
    setActiveSection(section);
    if (section === 'documents') {
      setActiveTab('Documents');
      return;
    }
    if (section === 'review-queue') {
      setActiveTab('Drafts');
      return;
    }
    setActiveTab('Overview');
  }, []);

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

  const renderDashboardPanel = () => {
    const matter = overview?.matter_details ?? null;
    const summaryCards = [
      { label: 'Matters', value: `${matters.length}` },
      { label: 'Files', value: `${overview?.documents.length ?? 0}` },
      { label: 'Tasks', value: `${overview?.open_tasks.length ?? 0}` },
      { label: 'Research items', value: `${overview?.research.length ?? 0}` },
    ];

    return (
      <main className="matter-workspace">
        <div className="workspace-heading">
          <div>
            <div className="eyebrow">Dashboard</div>
            <h1>Workspace overview</h1>
            <p>Jump into a matter, review totals, and switch quickly into documents, review, or team.</p>
          </div>
          <span className="status-badge">Overview</span>
        </div>
        {workspaceError && <div className="workspace-error">{workspaceError}</div>}
        <section className="overview-grid" aria-label="Workspace summary">
          {summaryCards.map(({ label, value }) => (
            <article className="overview-card" key={label}>
              <div className="overview-icon"><LayoutDashboard size={17} /></div>
              <div>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            </article>
          ))}
        </section>
        <section className="matter-summary">
          <h2>Recent matters</h2>
          {matters.length ? (
            <div className="matter-list">
              {matters.slice(0, 5).map((matterItem) => (
                <article key={matterItem.matter_id}>
                  <div>
                    <strong>{matterItem.title}</strong>
                    <span>{matterItem.case_number || matterItem.jurisdiction || 'Matter workspace'}</span>
                  </div>
                  <button className="source-action" type="button" onClick={() => void openMatter(matterItem.matter_id)}>
                    Open
                  </button>
                </article>
              ))}
            </div>
          ) : (
            <p>Create a matter to start using dashboard shortcuts.</p>
          )}
        </section>
        <section className="matter-summary">
          <h2>Selected matter</h2>
          {matter ? (
            <dl>
              <div><dt>Title</dt><dd>{matter.title}</dd></div>
              <div><dt>Status</dt><dd>{matter.status}</dd></div>
              <div><dt>Court</dt><dd>{matter.court || 'Not specified'}</dd></div>
              <div><dt>Files</dt><dd>{overview?.documents.length ?? 0}</dd></div>
            </dl>
          ) : (
            <p>No matter selected. Use the sidebar to open one.</p>
          )}
        </section>
      </main>
    );
  };

  const renderDocumentsPanel = () => {
    const documents = overview?.documents ?? [];

    return (
      <main className="matter-workspace">
        <div className="workspace-heading">
          <div>
            <div className="eyebrow">Documents</div>
            <h1>Matter files</h1>
            <p>Open the selected matter’s uploaded files and document summaries.</p>
          </div>
          <span className="status-badge">{documents.length} files</span>
        </div>
        {workspaceError && <div className="workspace-error">{workspaceError}</div>}
        {selectedMatterId ? (
          documents.length ? (
            <section className="matter-list">
              {documents.map((item, index) => (
                <article key={String(item.id || item.document_id || index)}>
                  <div>
                    <strong>{String(item.title || item.original_filename || 'Untitled document')}</strong>
                    <span>{String(item.status || item.upload_timestamp || '')}</span>
                  </div>
                </article>
              ))}
            </section>
          ) : (
            <section className="empty-panel">
              <div className="empty-mark"><FileStack size={27} /></div>
              <h2>No matter files yet</h2>
              <p>Upload documents in the selected matter to populate this section.</p>
            </section>
          )
        ) : (
          <section className="empty-panel">
            <div className="empty-mark"><FileStack size={27} /></div>
            <h2>Select a matter first</h2>
            <p>Choose a matter from the sidebar to view its documents.</p>
          </section>
        )}
      </main>
    );
  };

  const renderReviewQueuePanel = () => {
    const drafts = overview?.drafts ?? [];
    const tasks = overview?.open_tasks ?? [];

    return (
      <main className="matter-workspace">
        <div className="workspace-heading">
          <div>
            <div className="eyebrow">Review queue</div>
            <h1>Work to review</h1>
            <p>Track draft and task items that need attention for the current matter.</p>
          </div>
          <span className="status-badge">{drafts.length + tasks.length} items</span>
        </div>
        {workspaceError && <div className="workspace-error">{workspaceError}</div>}
        <section className="matter-summary">
          <h2>Drafts</h2>
          {drafts.length ? (
            <div className="matter-list">
              {drafts.map((item, index) => (
                <article key={String(item.id || item.draft_id || index)}>
                  <div>
                    <strong>{String(item.title || 'Draft')}</strong>
                    <span>{String(item.status || item.updated_at || '')}</span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p>No drafts awaiting review on this matter.</p>
          )}
        </section>
        <section className="matter-summary">
          <h2>Open tasks</h2>
          {tasks.length ? (
            <div className="matter-list">
              {tasks.map((item, index) => (
                <article key={String(item.id || item.task_id || index)}>
                  <div>
                    <strong>{String(item.title || 'Task')}</strong>
                    <span>{String(item.status || item.due_at || '')}</span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p>No open tasks for this matter.</p>
          )}
        </section>
      </main>
    );
  };

  const renderTeamPanel = () => {
    const parties = overview?.parties ?? [];
    const counsel = overview?.counsel ?? [];

    return (
      <main className="matter-workspace">
        <div className="workspace-heading">
          <div>
            <div className="eyebrow">Team</div>
            <h1>People on this matter</h1>
            <p>Review parties and counsel linked to the selected matter.</p>
          </div>
          <span className="status-badge">{parties.length + counsel.length} people</span>
        </div>
        {workspaceError && <div className="workspace-error">{workspaceError}</div>}
        <section className="matter-summary">
          <h2>Parties</h2>
          {parties.length ? (
            <div className="matter-list">
              {parties.map((item, index) => (
                <article key={String(item.id || item.party_id || index)}>
                  <div>
                    <strong>{String(item.name || item.title || 'Party')}</strong>
                    <span>{String(item.party_role || item.role || '')}</span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p>No parties have been added to this matter.</p>
          )}
        </section>
        <section className="matter-summary">
          <h2>Counsel</h2>
          {counsel.length ? (
            <div className="matter-list">
              {counsel.map((item, index) => (
                <article key={String(item.id || item.counsel_id || index)}>
                  <div>
                    <strong>{String(item.name || item.title || 'Counsel')}</strong>
                    <span>{String(item.party_role || item.role || '')}</span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p>No counsel have been linked to this matter.</p>
          )}
        </section>
      </main>
    );
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
            {navigation.map(({ label, icon: Icon, section }) => (
              <button
                key={label}
                className={activeSection === section ? 'active' : ''}
                onClick={() => handleNavigate(section)}
              >
                <Icon size={17} />{label}
              </button>
            ))}
            {matters.map((matter) => (
              <button
                className={`matter-nav-item ${selectedMatterId === matter.matter_id && activeSection === 'matters' ? 'active' : ''}`}
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
          {activeSection === 'dashboard' ? (
            renderDashboardPanel()
          ) : activeSection === 'documents' ? (
            renderDocumentsPanel()
          ) : activeSection === 'review-queue' ? (
            renderReviewQueuePanel()
          ) : activeSection === 'team' ? (
            renderTeamPanel()
          ) : (
            <MatterWorkspace
              overview={overview}
              activeTab={activeTab}
              isLoading={isWorkspaceLoading}
              error={workspaceError}
              onTabChange={(tab) => {
                setActiveSection('matters');
                setActiveTab(tab);
              }}
              onCreateMatter={() => setIsCreateOpen(true)}
            />
          )}
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
