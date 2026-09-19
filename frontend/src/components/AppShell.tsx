import { useState, type ReactNode } from 'react';
import { Activity, DoorOpen, Fan, History, LayoutDashboard, Menu, Route, TrainFront, X } from 'lucide-react';
import { mockMode } from '../api/client';
export const navigation = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard }, { id: 'door', label: 'Door', icon: DoorOpen },
  { id: 'acv', label: 'ACV', icon: Fan }, { id: 'rail', label: 'Rail Corrugation', icon: Route },
  { id: 'shm', label: 'Structural Health', icon: Activity }, { id: 'history', label: 'Run History', icon: History },
];
export function AppShell({ page, children }: { page: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return <div className="shell">
    <a className="skip-link" href="#main">Skip to content</a>
    <aside className="sidebar">
      <a href="#/overview" className="brand" onClick={() => setOpen(false)}><span className="brand-icon"><TrainFront size={25} /></span><span>FaultLine<small>ENGINEERING SYSTEMS</small></span></a>
      <button className="menu-toggle" aria-label={open ? 'Close navigation' : 'Open navigation'} aria-expanded={open} aria-controls="navigation" onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button>
      <nav id="navigation" className={open ? 'navigation open' : 'navigation'} aria-label="Main navigation"><p className="nav-label">CONDITION MONITORING</p>{navigation.map(({ id, label, icon: Icon }) => <a key={id} href={`#/${id}`} aria-current={page === id ? 'page' : undefined} onClick={() => setOpen(false)}><Icon size={19} />{label}</a>)}</nav>
      <div className="sidebar-foot"><span className="small-indicator" />PS3 · Analysis workspace<small>Recorded data · Four subsystems</small></div>
    </aside>
    <div className="workspace"><header className="topbar"><span>Train Condition Monitoring</span><span className="mode"><span className="small-indicator" />{mockMode ? 'Development fixtures' : 'Backend API mode'}</span></header>
      {mockMode && <div className="mock-banner" role="note">Development only · Results are synthetic fixtures, not analysis of your uploaded data. Do not use these exports for submission.</div>}
      <main id="main" tabIndex={-1}>{children}</main><footer>FaultLine / PS3 <span>Model findings support engineering review.</span></footer>
    </div>
  </div>;
}
