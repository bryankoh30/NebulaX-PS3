import { Activity, ArrowRight, DoorOpen, Fan, RefreshCw, Route } from 'lucide-react';
import type { Result, Run } from '../api/types';
import { config, subsystems, summary } from '../utils/domain';
import { useHistory } from '../hooks/useHistory';
import { EmptyState, ErrorState, LoadingState, StatusBadge } from '../components/States';

const icons = { door: DoorOpen, acv: Fan, rail: Route, shm: Activity };

function isAttentionFinding(run: Run, result: Result): boolean {
  if (run.subsystem === 'door') return 'prediction' in result && result.prediction === 'Abnormal resistance';
  if (run.subsystem === 'rail') return 'prediction' in result && result.prediction !== 'Normal';
  return run.subsystem === 'acv';
}

function findingText(result: Result): string {
  if ('ranked_cars' in result) return `Car ${result.ranked_cars[0] ?? '—'} ranked first`;
  if (typeof result.prediction === 'number') return `Estimated cumulative fatigue damage: ${result.prediction}`;
  return result.prediction;
}

export function OverviewPage() {
  const { latest, loading, error, reload } = useHistory(true);
  const findings = latest.flatMap((run, runOrder) => (run.results as Result[]).map((result, resultOrder) => ({
    run,
    result,
    runOrder,
    resultOrder,
    needsReview: result.review_status === 'unreviewed' && isAttentionFinding(run, result),
  }))).sort((left, right) => {
    if (left.needsReview !== right.needsReview) return left.needsReview ? -1 : 1;
    const timeDifference = Date.parse(right.run.created_at) - Date.parse(left.run.created_at);
    return timeDifference || left.runOrder - right.runOrder || left.resultOrder - right.resultOrder;
  });
  const visibleFindings = findings.slice(0, 12);

  return <>
    <div className="page-heading with-action"><div><p className="eyebrow">OPERATIONS WORKSPACE</p><h1>What needs attention?</h1><p>Latest completed analysis for each subsystem, with unreviewed attention findings surfaced first.</p></div><button className="secondary" onClick={reload} disabled={loading}><RefreshCw size={16} />Refresh</button></div>
    {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={reload} /> : <>
      <div className="summary-grid">{subsystems.map(subsystem => { const run = latest.find(item => item.subsystem === subsystem); const Icon = icons[subsystem]; return <a className="summary-card" key={subsystem} href={`#/${subsystem}${run ? `?run=${encodeURIComponent(run.run_id)}` : ''}`}><div className="summary-top"><span className="subsystem-icon"><Icon size={22} /></span><ArrowRight size={18} /></div><h2>{config[subsystem].name}</h2><strong>{run ? summary(run) : 'Awaiting first analysis'}</strong><p>{run ? 'Latest completed run' : config[subsystem].description}</p><span className="card-link">{run ? 'Open findings' : 'Upload recordings'} <ArrowRight size={14} /></span></a>; })}</div>
      <section className="card"><div className="section-heading"><div><h2>Review queue</h2><p>Findings from each subsystem's latest completed run</p></div><a className="text-link" href="#/history">Run history <ArrowRight size={15} /></a></div>
        {visibleFindings.length ? <div className="table-scroll"><table><caption className="sr-only">Latest findings with unreviewed attention findings first</caption><thead><tr><th>Subsystem</th><th>Finding</th><th>Review status</th><th>Source / upload time</th></tr></thead><tbody>{visibleFindings.map(({ run, result, needsReview }) => <tr key={result.result_id} className={needsReview ? 'priority-finding' : undefined}><td><a className="text-link" href={`#/${run.subsystem}?run=${encodeURIComponent(run.run_id)}`}>{config[run.subsystem].name}</a></td><td>{findingText(result)}{needsReview && <span className="cell-note attention-label">Needs review</span>}</td><td><StatusBadge value={result.review_status ?? 'unreviewed'} /></td><td>{'file_id' in result ? result.file_id : run.files.join(', ')}<small className="cell-note">Latest run · {run.created_at}</small></td></tr>)}</tbody></table></div> : <EmptyState title="Your findings will appear here" text="Start with a subsystem above and upload a recording for analysis." />}
        {findings.length > visibleFindings.length && <p className="muted">Showing the first {visibleFindings.length} prioritised findings. Open a subsystem to review its complete latest run.</p>}
      </section>
      <div className="info-strip"><Activity size={22} /><div><strong>Four subsystems. Different questions.</strong><p>Door and Rail classify patterns. ACV ranks suspected cars. Structural Health estimates cumulative fatigue damage. Operators review each result against its own engineering procedures.</p></div></div>
    </>}
  </>;
}
