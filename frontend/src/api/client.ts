import type { ApiClient, Run, RunSummary, Review, ReviewEvent } from './types';

const base = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
export const mockMode = import.meta.env.DEV && import.meta.env.VITE_USE_MOCK_API === 'true';
export const capabilities = {
  reviews: import.meta.env.VITE_ENABLE_REVIEWS !== 'false',
  zip: !mockMode && import.meta.env.VITE_ENABLE_ZIP_EXPORT !== 'false',
};
export function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.';
}
async function request(path: string, options: RequestInit = {}): Promise<Response> {
  let response: Response;
  try { response = await fetch(`${base}/api${path}`, options); }
  catch (error) {
    if (options.signal?.aborted) throw error;
    throw new Error('Cannot reach the analysis service. Check the backend connection and try again.');
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.error?.message ?? body?.detail?.message ?? body?.message ?? body?.detail;
    const validation = Array.isArray(detail) ? detail.map(item => `${item.loc?.slice(1).join('.') || 'Request'}: ${item.msg}`).join('; ') : null;
    throw new Error(typeof detail === 'string' ? detail : validation ?? `The service could not complete this request (HTTP ${response.status}).`);
  }
  return response;
}
async function json<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await request(path, options);
  if (!response.headers.get('content-type')?.includes('application/json')) {
    throw new Error('The service returned an unexpected response. Check the API connection.');
  }
  return response.json() as Promise<T>;
}
async function download(path: string, options?: RequestInit) {
  const response = await request(path, options);
  if (response.headers.get('content-type')?.includes('text/html')) throw new Error('The export endpoint returned a web page instead of a file.');
  return response.blob();
}
const realClient: ApiClient = {
  createRun(subsystem, files, signal) {
    const body = new FormData(); body.append('subsystem', subsystem);
    files.forEach(file => body.append('files', file));
    return json('/runs', { method: 'POST', body, signal });
  },
  getRun: (id, signal) => json<Run>(`/runs/${encodeURIComponent(id)}`, { signal }),
  listRuns: signal => json<RunSummary[]>('/runs', { signal }),
  exportRun: (id, signal) => download(`/runs/${encodeURIComponent(id)}/export`, { signal }),
  async reviewResult(id, status, note, signal) {
    const result = await json<Review>(`/results/${encodeURIComponent(id)}/review`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status, note }), signal,
    });
    // The endpoint returns the whole result; only review metadata may update UI state.
    return { review_status: result.review_status, review_note: result.review_note };
  },
  getReviews: (id, signal) => json<ReviewEvent[]>(`/results/${encodeURIComponent(id)}/reviews`, { signal }),
  exportZip: (run_ids, signal) => download('/exports', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ run_ids }), signal,
  }),
};
// Production builds cannot enable fixtures, even with VITE_USE_MOCK_API=true.
export const api: ApiClient = mockMode ? (await import('./mockClient')).mockClient : realClient;
