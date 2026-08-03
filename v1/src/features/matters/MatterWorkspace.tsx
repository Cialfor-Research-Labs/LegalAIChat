import { CalendarDays, CheckCircle2, Clock3, FileText, Scale } from 'lucide-react';
import { MatterOverview } from '../../core/api';

const tabs = ['Overview', 'Timeline', 'Tasks', 'Documents', 'Research', 'Drafts'] as const;
type MatterTab = typeof tabs[number];

interface MatterWorkspaceProps {
  overview: MatterOverview | null;
  activeTab: MatterTab;
  isLoading: boolean;
  error: string | null;
  onTabChange: (tab: MatterTab) => void;
  onCreateMatter: () => void;
}

function itemTitle(item: Record<string, unknown>): string {
  return String(item.title || item.original_filename || item.content || 'Untitled item');
}

export function MatterWorkspace({
  overview,
  activeTab,
  isLoading,
  error,
  onTabChange,
  onCreateMatter,
}: MatterWorkspaceProps) {
  const matter = overview?.matter_details;
  const nextHearing = overview?.hearings[0];
  const tabItems: Record<MatterTab, Record<string, unknown>[]> = {
    Overview: [],
    Timeline: overview?.timeline_events ?? [],
    Tasks: overview?.open_tasks ?? [],
    Documents: overview?.documents ?? [],
    Research: overview?.research ?? [],
    Drafts: overview?.drafts ?? [],
  };
  const overviewItems = [
    { label: 'Court', value: matter?.court || 'Not specified', icon: Scale },
    { label: 'Next hearing', value: nextHearing ? itemTitle(nextHearing) : 'No hearing linked', icon: CalendarDays },
    { label: 'Open tasks', value: `${overview?.open_tasks.length ?? 0} tasks`, icon: CheckCircle2 },
    { label: 'Matter files', value: `${overview?.documents.length ?? 0} files`, icon: FileText },
  ];

  return (
    <main className="matter-workspace">
      <div className="workspace-heading">
        <div>
          <div className="eyebrow">Matter workspace</div>
          <h1>{matter?.title || 'No matter selected'}</h1>
          <p>{matter?.description || 'Create or select a matter to begin working.'}</p>
        </div>
        <span className="status-badge"><Clock3 size={14} /> {matter?.status || 'Not connected'}</span>
      </div>

      {error && <div className="workspace-error">{error}</div>}

      <section className="overview-grid" aria-label="Matter overview">
        {overviewItems.map(({ label, value, icon: Icon }) => (
          <article className="overview-card" key={label}>
            <div className="overview-icon"><Icon size={17} /></div>
            <div><span>{label}</span><strong>{value}</strong></div>
          </article>
        ))}
      </section>

      <nav className="matter-tabs" aria-label="Matter sections">
        {tabs.map((tab) => (
          <button
            className={activeTab === tab ? 'active' : ''}
            disabled={!overview}
            key={tab}
            onClick={() => onTabChange(tab)}
          >
            {tab}
          </button>
        ))}
      </nav>

      {isLoading ? (
        <section className="empty-panel"><p>Loading matter workspace…</p></section>
      ) : !overview ? (
        <section className="empty-panel">
          <div className="empty-mark"><Scale size={27} /></div>
          <h2>Create your first matter</h2>
          <p>Connect parties, hearings, files, tasks, research, and drafts to one matter record.</p>
          <button onClick={onCreateMatter}>Create first matter</button>
        </section>
      ) : activeTab === 'Overview' ? (
        <section className="matter-summary">
          <h2>Matter details</h2>
          <dl>
            <div><dt>Case number</dt><dd>{matter?.case_number || 'Not specified'}</dd></div>
            <div><dt>Jurisdiction</dt><dd>{matter?.jurisdiction || 'Not specified'}</dd></div>
            <div><dt>Stage</dt><dd>{matter?.stage || 'Not specified'}</dd></div>
            <div><dt>Parties</dt><dd>{overview.parties.length}</dd></div>
          </dl>
        </section>
      ) : (
        <section className="matter-list">
          {tabItems[activeTab].length ? tabItems[activeTab].map((item, index) => (
            <article key={String(item.id || item.document_id || item.draft_id || index)}>
              <strong>{itemTitle(item)}</strong>
              <span>{String(item.status || item.created_at || '')}</span>
            </article>
          )) : <p>No {activeTab.toLowerCase()} have been added to this matter.</p>}
        </section>
      )}
    </main>
  );
}

export type { MatterTab };
