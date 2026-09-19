import { ArrowRight, RefreshCw, Activity, DoorOpen, Fan, Route } from 'lucide-react';
import type { Result } from '../api/types';
import { config, subsystems, summary, uploadMetadata } from '../utils/domain';
import { useHistory } from '../hooks/useHistory';
import { EmptyState, ErrorState, LoadingState, StatusBadge } from '../components/States';
const icons = { door: DoorOpen, acv: Fan, rail: Route, shm: Activity };
export function OverviewPage() {
  const { latest, loading, error, reload } = useHistory(true);
  return <><div className="page-heading with-action"><div><p className="eyebrow">OPERATIONS WORKSPACE</p><h1>What needs attention?</h1><p>Latest completed analysis for each subsystem, ready for engineering review.</p></div><button className="secondary" onClick={reload} disabled={loading}><RefreshCw size={16} />Refresh</button></div>
    {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={reload} /> : <>
      <div className="summary-grid">{subsystems.map(subsystem => { const run = latest.find(run => run.subsystem === subsystem); const Icon = icons[subsystem]; return <a className="summary-card" key={subsystem} href={`#/${subsystem}${run ? `?run=${encodeURIComponent(run.run_id)}` : ''}`}><div className="summary-top"><span className="subsystem-icon"><Icon size={22} /></span><ArrowRight size={18} /></div><h2>{config[subsystem].name}</h2><strong>{run ? summary(run) : 'Awaiting first analysis'}</strong><p>{run ? 'Latest completed run' : config[subsystem].description}</p><span className="card-link">{run ? 'Open findings' : 'Upload recordings'} <ArrowRight size={14} /></span></a>; })}</div>
      <section className="card"><div className="section-heading"><div><h2>Recent findings</h2><p>From the latest completed run in each subsystem</p></div><a className="text-link" href="#/history">Run history <ArrowRight size={15} /></a></div>
        {latest.some(run => run.results.length) ? <div className="table-scroll"><table><caption className="sr-only">Recent model findings</caption><thead><tr><th>Subsystem</th><th>Finding</th><th>Review status</th><th>Source / upload time</th></tr></thead><tbody>{latest.flatMap(run => (run.results as Result[]).slice(0, 5).map(result => <tr key={result.result_id}><td><a className="text-link" href={`#/${run.subsystem}?run=${encodeURIComponent(run.run_id)}`}>{config[run.subsystem].name}</a></td><td>{'ranked_cars' in result ? `Car ${result.ranked_cars[0] ?? '—'} ranked first` : typeof result.prediction === 'number' ? `Estimated damage: ${result.prediction}` : result.prediction}</td><td><StatusBadge value={result.review_status ?? 'unreviewed'} /></td><td>{'file_id' in result ? result.file_id : uploadMetadata(run.run_id)?.filenames.join(', ') ?? 'Continuous door recording'}<small className="cell-note">{uploadMetadata(run.run_id)?.submittedAt ?? 'Upload time unavailable'}</small></td></tr>))}</tbody></table></div> : <EmptyState title="Your findings will appear here" text="Start with a subsystem above and upload a recording for analysis." />}
        {latest.some(run => run.results.length > 5) && <p className="muted">Showing up to five findings per subsystem. Open a run to see all results.</p>}
      </section>
      <div className="info-strip"><Activity size={22} /><div><strong>Four subsystems. Different questions.</strong><p>Door and Rail classify patterns. ACV ranks suspected cars. Structural Health estimates fatigue damage. Review each result in its own context.</p></div></div>
    </>}
  </>;
}
