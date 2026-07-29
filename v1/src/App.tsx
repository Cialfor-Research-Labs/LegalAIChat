import { Bell, BriefcaseBusiness, ChevronDown, Command, FileStack, LayoutDashboard, Search, Settings, Users } from 'lucide-react';
import { betaConfig } from './core/betaConfig';
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

export function App() {
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
          <div className="profile">VA</div>
          <ChevronDown size={15} />
        </div>
      </header>

      <div className="app-frame">
        <aside className="primary-sidebar">
          <button className="new-matter" disabled>+ New matter</button>
          <nav>
            {navigation.map(({ label, icon: Icon, active }) => (
              <button className={active ? 'active' : ''} disabled key={label}><Icon size={17} />{label}</button>
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
