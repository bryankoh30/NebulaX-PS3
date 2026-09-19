import type { Subsystem } from '../api/types';
import { useRun } from '../hooks/useRun';
import { config } from '../utils/domain';
import { UploadZone } from '../components/UploadZone';
import { EmptyState, ErrorState, LoadingState, StatusBadge, statusText } from '../components/States';
import { Results } from '../components/Results';
export function SubsystemPage({ subsystem, runId }: { subsystem: Subsystem; runId?: string }) {
  const { run, setRun, error, uploading, loading, start, retry } = useRun(subsystem, runId);
  const busy = uploading || loading || (!!run && ['queued', 'running'].includes(run.status) && !error);
  return <><div className="page-heading"><p className="eyebrow">SUBSYSTEM ANALYSIS</p><h1>{config[subsystem].name}</h1><p>{config[subsystem].description}</p></div>
    <UploadZone subsystem={subsystem} busy={busy} onAnalyse={files => void start(files)} />
    {error && <ErrorState message={error} retry={runId ? retry : undefined} />}
    {uploading && <LoadingState text="Uploading recordings…" />}
    {loading && <LoadingState text="Loading run…" />}
    {run && <div className="run-meta"><span>Run <code>{run.run_id}</code> · {run.files.join(', ')} · {run.created_at}</span><StatusBadge value={run.status} /></div>}
    {run && ['queued', 'running'].includes(run.status) && !error && <LoadingState text={statusText[run.status]} />}
    {run?.status === 'failed' && <ErrorState message={run.error?.message ?? 'The analysis failed. Select recordings and try again.'} />}
    {run?.status === 'completed' && <Results key={run.run_id} run={run} onUpdate={setRun} />}
    {!run && !loading && !uploading && !error && <EmptyState />}
  </>;
}
