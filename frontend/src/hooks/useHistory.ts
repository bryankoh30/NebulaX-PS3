import { useEffect, useState } from 'react';
import { api, messageOf } from '../api/client';
import type { Run, RunSummary } from '../api/types';
export function useHistory(withLatest: boolean) {
  const [runs, setRuns] = useState<RunSummary[]>([]); const [latest, setLatest] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError('');
    void (async () => {
      try {
        const summaries = await api.listRuns(controller.signal);
        if (!Array.isArray(summaries)) throw new Error('The run history response does not match the planned API contract.');
        const seen = new Set<string>();
        const latestSummaries = summaries.filter(run => { if (run.status !== 'completed' || seen.has(run.subsystem)) return false; seen.add(run.subsystem); return true; });
        const details = withLatest ? await Promise.all(latestSummaries.map(run => api.getRun(run.run_id, controller.signal))) : [];
        if (!controller.signal.aborted) { setRuns(summaries); setLatest(details); }
      } catch (error) { if (!controller.signal.aborted) setError(messageOf(error)); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    })();
    return () => controller.abort();
  }, [version, withLatest]);
  return { runs, latest, loading, error, reload: () => setVersion(value => value + 1) };
}
