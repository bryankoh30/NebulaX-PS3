import { useState } from 'react';
import { Download, RefreshCw } from 'lucide-react';
import { api, capabilities, messageOf } from '../api/client';
import { useHistory } from '../hooks/useHistory';
import { config, saveBlob, subsystems, uploadMetadata } from '../utils/domain';
import { EmptyState, ErrorState, LoadingState, StatusBadge } from '../components/States';
export function HistoryPage() {
  const { runs, loading, error, reload } = useHistory(false); const [selected, setSelected] = useState<string[]>([]); const [exportError, setExportError] = useState(''); const [busy, setBusy] = useState(false);
  const chosen = runs.filter(run => selected.includes(run.run_id));
  const validZip = chosen.length === 4 && subsystems.every(subsystem => chosen.filter(run => run.subsystem === subsystem && run.status === 'completed').length === 1);
  return <><div className="page-heading with-action"><div><p className="eyebrow">ANALYSIS RECORD</p><h1>Run History</h1><p>Reopen previous analyses and download completed results.</p></div><button className="secondary" onClick={reload} disabled={loading}><RefreshCw size={16} />Refresh</button></div>
    {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={reload} /> : <section className="card"><div className="section-heading"><div><h2>All runs</h2><p>Newest first · {runs.length} runs</p></div>{capabilities.zip && <button className="secondary" disabled={!validZip || busy} onClick={async () => { setBusy(true); setExportError(''); try { saveBlob(await api.exportZip(selected), 'predictions.zip'); } catch (error) { setExportError(messageOf(error)); } finally { setBusy(false); } }}><Download size={16} />{busy ? 'Preparing export…' : 'Download predictions.zip'}</button>}</div>
      {capabilities.zip && <p>Select exactly one completed run per subsystem for the final ZIP.</p>}{exportError && <ErrorState message={exportError} />}
      {runs.length ? <div className="table-scroll"><table><caption className="sr-only">Run history, newest first</caption><thead><tr>{capabilities.zip && <th>Export</th>}<th>Subsystem</th><th>Uploaded files</th><th>Status</th><th>Upload timestamp</th><th>Results</th></tr></thead><tbody>{runs.map(run => { const metadata = uploadMetadata(run.run_id); return <tr key={run.run_id}>{capabilities.zip && <td><input type="checkbox" aria-label={`Select ${config[run.subsystem].name} run ${run.run_id}`} disabled={run.status !== 'completed'} checked={selected.includes(run.run_id)} onChange={event => setSelected(event.target.checked ? [...selected, run.run_id] : selected.filter(id => id !== run.run_id))} /></td>}<td>{config[run.subsystem].name}</td><td>{metadata?.filenames.length ?? 'Unavailable'}{metadata && <span className="cell-note">{metadata.filenames.join(', ')}</span>}</td><td><StatusBadge value={run.status} /></td><td className="timestamp">{metadata?.submittedAt ?? 'Unavailable'}</td><td><a className="text-link" href={`#/${run.subsystem}?run=${encodeURIComponent(run.run_id)}`}>{run.status === 'completed' ? 'Open results' : 'Open run'}</a></td></tr>; })}</tbody></table></div> : <EmptyState title="No runs yet" text="Your analyses will appear here after you upload recordings." />}
      <p className="muted">Upload times and file counts are available for uploads made in this browser tab. Backend history metadata is not yet defined in the API plan.</p>
    </section>}
  </>;
}
