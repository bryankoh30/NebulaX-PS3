import { useCallback, useEffect, useRef, useState } from 'react';
import { api, messageOf } from '../api/client';
import type { Run, Subsystem } from '../api/types';
export function useRun(subsystem: Subsystem, runId?: string) {
  const [run, setRun] = useState<Run | null>(null); const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false); const [loading, setLoading] = useState(!!runId);
  const [retry, setRetry] = useState(0); const uploadController = useRef<AbortController | null>(null);
  useEffect(() => () => uploadController.current?.abort(), []);
  useEffect(() => {
    if (!runId) return;
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout> | undefined;
    setLoading(true); setError('');
    async function poll() {
      try {
        const next = await api.getRun(runId!, controller.signal);
        if (controller.signal.aborted) return;
        if (next.subsystem !== subsystem) throw new Error('This run belongs to a different subsystem. Open it from Run History.');
        setRun(next); setLoading(false);
        if (next.status === 'queued' || next.status === 'running') timer = setTimeout(poll, 1000);
      } catch (error) { if (!controller.signal.aborted) { setError(messageOf(error)); setLoading(false); } }
    }
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [runId, subsystem, retry]);
  const start = useCallback(async (files: File[]) => {
    uploadController.current?.abort(); const controller = new AbortController(); uploadController.current = controller;
    setUploading(true); setError('');
    try {
      const created = await api.createRun(subsystem, files, controller.signal);
      if (controller.signal.aborted) return;
      location.hash = `#/${subsystem}?run=${encodeURIComponent(created.run_id)}`;
    } catch (error) { if (!controller.signal.aborted) setError(messageOf(error)); }
    finally { if (!controller.signal.aborted) setUploading(false); }
  }, [subsystem]);
  return { run, setRun, error, uploading, loading, start, retry: () => setRetry(value => value + 1) };
}
