import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { ClipboardCheck, Download, X } from 'lucide-react';
import type { AcvResult, DoorResult, RailResult, Result, Run, Review, ReviewStatus } from '../api/types';
import { api, capabilities, messageOf, mockMode } from '../api/client';
import { saveBlob, summary } from '../utils/domain';
import { EmptyState, ErrorState, StatusBadge } from './States';
import { ReviewHistory } from './ReviewHistory';
const ChartCard = lazy(() => import('./ChartCard').then(module => ({ default: module.ChartCard })));
const AcvComparisonChart = lazy(() => import('./AcvComparisonChart').then(module => ({ default: module.AcvComparisonChart })));

function reviewNext(run: Run, result: Result): string {
  if (run.subsystem === 'door') {
    return (result as DoorResult).prediction === 'Abnormal resistance'
      ? 'Check the motor-current and door-position traces, then follow the approved inspection procedure for mechanical sources of abnormal resistance.'
      : 'Check the motor-current and door-position traces to confirm the movement is consistent with expected operation before closing the review.';
  }
  if (run.subsystem === 'acv') {
    const ranking = (result as AcvResult).ranked_cars;
    const next = ranking.slice(1, 3).map(car => `Car ${car}`).join(' and ');
    return `Prioritise Car ${ranking[0] ?? 'at the top of the ranking'} for inspection${next ? `, then check ${next} if further investigation is needed` : ''}. Use the ranking to guide review, not as an automated maintenance decision.`;
  }
  if (run.subsystem === 'rail') {
    const prediction = (result as RailResult).prediction;
    return prediction === 'Normal'
      ? 'Review the supporting vibration signal and confirm that no affected side was identified before deciding whether physical inspection is warranted.'
      : `Review ${prediction} and its supporting vibration signal before deciding whether to proceed with physical inspection under approved procedures.`;
  }
  return "Compare the estimated cumulative fatigue damage with the operator's approved engineering limits and procedures. The model does not make a maintenance or safety decision.";
}

function ReviewForm({ result, onSaved }: { result: Result; onSaved: (review: Review) => void }) {
  const [status, setStatus] = useState<ReviewStatus>(result.review_status);
  const [note, setNote] = useState(result.review_note ?? ''); const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [saved, setSaved] = useState(false);
  return <form className="review-form" onSubmit={async event => {
    event.preventDefault(); setBusy(true); setError(''); setSaved(false);
    try { const review = await api.reviewResult(result.result_id, status, note); onSaved(review); setSaved(true); }
    catch (error) { setError(messageOf(error)); } finally { setBusy(false); }
  }}><h3>Engineering review</h3><p>Review decisions are recorded separately from the model prediction.</p><label htmlFor="review-status">Review status</label><select id="review-status" value={status} onChange={e => { setStatus(e.target.value as ReviewStatus); setSaved(false); }}><option value="unreviewed">Unreviewed</option><option value="confirmed">Confirm</option><option value="dismissed">Dismiss</option><option value="resolved">Resolve</option></select><label htmlFor="review-note">Add note</label><textarea id="review-note" rows={3} maxLength={2000} value={note} onChange={e => { setNote(e.target.value); setSaved(false); }} /><button className="primary" disabled={busy}>{busy ? 'Saving…' : 'Save review'}</button>{saved && <p role="status">Review saved.</p>}{error && <ErrorState message={error} />}</form>;
}
function Detail({ run, result, onClose, onSaved }: { run: Run; result: Result; onClose: () => void; onSaved: (review: Review) => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [reviewVersion, setReviewVersion] = useState(0);
  useEffect(() => {
    const node = dialog.current!;
    node.showModal();
    node.querySelector<HTMLButtonElement>('[aria-label="Close details"]')?.focus({ preventScroll: true });
    return () => node.close();
  }, []);
  const file = 'file_id' in result ? result.file_id : null;
  const charts = run.chart_series.filter(series => file === null || series.file_id === file);
  const abnormalDoor = run.subsystem === 'door' && 'prediction' in result && result.prediction === 'Abnormal resistance';
  let title: string; let explanation: string;
  if (run.subsystem === 'acv') { title = 'Most likely affected car'; explanation = "The ranking compares each car's behaviour with peer cars in the same recording."; }
  else if (run.subsystem === 'shm') { title = 'Estimated cumulative fatigue damage'; explanation = "This value is the model's estimate of cumulative fatigue damage from the supplied stress recording. Interpret it against the operator's approved engineering limits and procedures; it is not a safety classification, failure probability, or remaining-life estimate."; }
  else if (run.subsystem === 'door') { title = abnormalDoor ? 'Abnormal resistance detected' : 'Normal door movement'; explanation = abnormalDoor ? 'The model detected unusual resistance during this door movement cycle.' : 'No abnormal resistance was detected in this door movement cycle.'; }
  else { const prediction = 'prediction' in result ? result.prediction : ''; title = `Condition: ${prediction}`; explanation = prediction === 'Normal' ? 'No corrugation pattern was detected in this recording.' : `The model detected a vibration pattern consistent with rail corrugation on ${prediction}.`; }
  return <dialog ref={dialog} className="detail-panel" aria-labelledby="detail-title" onCancel={onClose} onClick={event => { if (event.target === dialog.current) onClose(); }}><div className="detail-content"><div className="section-heading"><p className="eyebrow">FINDING DETAILS</p><button autoFocus className="icon-button" aria-label="Close details" onClick={onClose}><X /></button></div><h2 id="detail-title">{title}</h2><p className="filename">{file ?? `${(result as DoorResult).start_time} → ${(result as DoorResult).end_time}`}</p>
    {run.subsystem === 'acv' ? <><div className="detail-value">Car {(result as AcvResult).ranked_cars[0] ?? '—'}</div><ol className="ranking">{(result as AcvResult).ranked_cars.map(car => <li key={car}>Car {car}</li>)}</ol></> : 'prediction' in result && <div className="detail-value">{typeof result.prediction === 'number' ? String(result.prediction) : <StatusBadge value={result.prediction} />}</div>}
    <p className="explanation">{explanation}</p>
    {run.subsystem === 'rail' && 'prediction' in result && <p><strong>Affected side:</strong> {result.prediction === 'Normal' ? 'None' : result.prediction}</p>}
    {abnormalDoor && <div className="context-box"><h3>Possible causes to inspect</h3><p>Contextual examples, not detected causes:</p><ul><li>Obstruction</li><li>Rubber strip jamming</li><li>Door deformation</li><li>Mechanical resistance</li></ul></div>}
    <section className="review-next" aria-labelledby="review-next-title"><ClipboardCheck size={19} /><div><h3 id="review-next-title">Review next</h3><p>{reviewNext(run, result)}</p></div></section>
    <h3>Signal context</h3>{charts.length ? <Suspense fallback={<p role="status">Loading chart…</p>}>{run.subsystem === 'acv' ? <AcvComparisonChart series={charts} rankedCars={(result as AcvResult).ranked_cars} /> : charts.map(series => <ChartCard key={`${series.file_id}-${series.series_id}`} series={series} cycle={run.subsystem === 'door' ? result as DoorResult : undefined} />)}</Suspense> : <p className="evidence-empty">No signal context was supplied for this finding.</p>}
    <div className="review-status"><strong>Review status</strong><StatusBadge value={result.review_status ?? 'unreviewed'} /></div>{result.review_note && <p className="saved-note">{result.review_note}</p>}
    {capabilities.reviews && <><ReviewForm result={result} onSaved={review => { onSaved(review); setReviewVersion(version => version + 1); }} /><ReviewHistory resultId={result.result_id} version={reviewVersion} /></>}
  </div></dialog>;
}
export function Results({ run, onUpdate }: { run: Run; onUpdate: (run: Run) => void }) {
  const [filter, setFilter] = useState('All'); const [selected, setSelected] = useState<string | null>(null); const [error, setError] = useState(''); const [downloading, setDownloading] = useState(false);
  const rows = (run.results as Result[]).filter(result => run.subsystem !== 'rail' || filter === 'All' || ('prediction' in result && result.prediction === filter));
  const current = (run.results as Result[]).find(result => result.result_id === selected);
  async function download() {
    setDownloading(true); setError('');
    try { saveBlob(await api.exportRun(run.run_id), `${run.subsystem}_predictions.csv`); } catch (error) { setError(messageOf(error)); } finally { setDownloading(false); }
  }
  return <>
    <section className="result-summary"><div><p className="eyebrow">ANALYSIS SUMMARY</p><h2>{summary(run)}</h2><p>{run.subsystem === 'door' ? `${run.results.length} total cycles · ${run.results.filter(r => r.prediction === 'Normal').length} Normal` : 'Select a finding to inspect its explanation and signal context.'}</p></div><StatusBadge value="completed" /></section>
    <section className="card results-card"><div className="section-heading"><div><h2>{run.subsystem === 'door' ? 'Detected cycles' : 'Recording results'}</h2><p>{run.results.length} {run.subsystem === 'door' ? 'cycles' : 'recordings'} in this run</p></div><button className="secondary" disabled={downloading} onClick={download}><Download size={16} />{downloading ? 'Preparing download…' : `Download ${run.subsystem}_predictions.csv`}</button></div>
      {mockMode && <p className="muted">Development fixture export · not for submission</p>}{error && <ErrorState message={error} retry={download} />}
      {run.subsystem === 'rail' && <div className="filters" role="group" aria-label="Filter predictions">{['All', 'Normal', 'Side I', 'Side II'].map(label => <button key={label} aria-pressed={filter === label} onClick={() => setFilter(label)}>{label}</button>)}</div>}
      {rows.length ? <div className="table-scroll"><table><caption className="sr-only">Analysis results</caption><thead><tr><th>{run.subsystem === 'door' ? 'Cycle' : 'File'}</th>{run.subsystem === 'door' && <><th>Start time</th><th>End time</th></>}<th>{run.subsystem === 'shm' ? 'Estimated cumulative fatigue damage' : run.subsystem === 'acv' ? 'Most likely affected car' : 'Prediction'}</th><th>Review status</th></tr></thead><tbody>{rows.map((result, i) => <tr key={result.result_id}><td><button className="result-link" onClick={() => setSelected(result.result_id)}>{'file_id' in result ? result.file_id : `Cycle ${i + 1}`}</button></td>{'start_time' in result && <><td className="timestamp">{result.start_time}</td><td className="timestamp">{result.end_time}</td></>}<td>{'ranked_cars' in result ? <><strong>Car {result.ranked_cars[0] ?? '—'}</strong><span className="cell-note">{result.ranked_cars.length} cars ranked · open for full ranking</span></> : typeof result.prediction === 'number' ? <span className="numeric">{String(result.prediction)}</span> : <StatusBadge value={result.prediction} />}</td><td><StatusBadge value={result.review_status ?? 'unreviewed'} /></td></tr>)}</tbody></table></div> : <EmptyState title={run.results.length ? 'No matching findings' : 'No results returned'} text={run.results.length ? 'Select another prediction filter.' : 'The completed run contains no detected results.'} />}
    </section>
    {current && <Detail key={current.result_id} run={run} result={current} onClose={() => setSelected(null)} onSaved={review => onUpdate({ ...run, results: run.results.map(result => result.result_id === current.result_id ? { ...result, ...review } : result) } as Run)} />}
  </>;
}
