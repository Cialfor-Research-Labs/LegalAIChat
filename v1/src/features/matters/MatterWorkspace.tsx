import { CalendarDays, CheckCircle2, Clock3, FileText, Scale } from 'lucide-react';

const overviewItems = [
  { label: 'Court', value: 'Not connected', icon: Scale },
  { label: 'Next hearing', value: 'No hearing linked', icon: CalendarDays },
  { label: 'Open tasks', value: '0 tasks', icon: CheckCircle2 },
  { label: 'Matter files', value: '0 files', icon: FileText },
];

export function MatterWorkspace() {
  return (
    <main className="matter-workspace">
      <div className="workspace-heading">
        <div>
          <div className="eyebrow">Matter workspace</div>
          <h1>New matter</h1>
          <p>This is a visual shell. Matter data and actions are intentionally not connected.</p>
        </div>
        <span className="status-badge"><Clock3 size={14} /> Draft workspace</span>
      </div>

      <section className="overview-grid" aria-label="Matter overview">
        {overviewItems.map(({ label, value, icon: Icon }) => (
          <article className="overview-card" key={label}>
            <div className="overview-icon"><Icon size={17} /></div>
            <div>
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          </article>
        ))}
      </section>

      <nav className="matter-tabs" aria-label="Matter sections">
        {['Overview', 'Timeline', 'Tasks', 'Documents', 'Research', 'Drafts'].map((tab, index) => (
          <button className={index === 0 ? 'active' : ''} disabled key={tab}>{tab}</button>
        ))}
      </nav>

      <section className="empty-panel">
        <div className="empty-mark"><Scale size={27} /></div>
        <h2>Your matter workspace will appear here</h2>
        <p>Parties, hearings, deadlines, files, tasks, research, and draft versions will be assembled around one matter record.</p>
        <button disabled>Create first matter</button>
      </section>
    </main>
  );
}
