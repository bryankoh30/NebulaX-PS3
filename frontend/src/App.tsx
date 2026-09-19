import { useEffect, useState } from 'react';
import { AppShell } from './components/AppShell';
import { OverviewPage } from './pages/OverviewPage';
import { HistoryPage } from './pages/HistoryPage';
import { SubsystemPage } from './pages/SubsystemPage';
import { subsystems } from './utils/domain';
import type { Subsystem } from './api/types';
function route() {
  const [path, query] = location.hash.replace(/^#\/?/, '').split('?');
  const page = [...subsystems, 'history', 'overview'].includes(path) ? path : 'overview';
  return { page, runId: new URLSearchParams(query).get('run') ?? undefined };
}
export default function App() {
  const [current, setCurrent] = useState(route);
  useEffect(() => { const change = () => { setCurrent(route()); window.scrollTo(0, 0); }; window.addEventListener('hashchange', change); return () => window.removeEventListener('hashchange', change); }, []);
  return <AppShell page={current.page}>{current.page === 'overview' ? <OverviewPage /> : current.page === 'history' ? <HistoryPage /> : <SubsystemPage key={`${current.page}-${current.runId ?? 'new'}`} subsystem={current.page as Subsystem} runId={current.runId} />}</AppShell>;
}
