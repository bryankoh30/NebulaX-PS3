// Development fixtures only. Does not read recordings or perform inference.
import type { ApiClient, Run, Subsystem, Result, ChartSeries } from './types';
const key = 'ps3-development-fixtures-v1';
interface Stored { run: Run; started: number; fail: boolean }
function read(): Stored[] { try { return JSON.parse(sessionStorage.getItem(key) ?? '[]'); } catch { return []; } }
function write(items: Stored[]) { sessionStorage.setItem(key, JSON.stringify(items)); }
function check(signal?: AbortSignal) { signal?.throwIfAborted(); }
function fixture(subsystem: Subsystem, files: File[], run_id: string): Run {
  const common = { run_id, status: 'queued' as const, error: null, chart_series: [] as ChartSeries[] };
  const review = { review_status: 'unreviewed' as const, review_note: null };
  const id = (i: number) => `${run_id}-${i}`;
  switch (subsystem) {
    case 'rail': return { ...common, subsystem, results: files.map((file, i) => ({ ...review, result_id: id(i), file_id: file.name, prediction: (['Normal', 'Side I', 'Side II'] as const)[i % 3] })) };
    case 'shm': return { ...common, subsystem, results: files.map((file, i) => ({ ...review, result_id: id(i), file_id: file.name, prediction: 0.00482 + i * 0.00123 })) };
    case 'acv': return { ...common, subsystem, results: files.map((file, i) => ({ ...review, result_id: id(i), file_id: file.name, ranked_cars: ['03', '05', '02', '01', '04', '06', '07', '08'] })) };
    case 'door': return { ...common, subsystem, results: [0, 1, 2, 3].map(i => ({ ...review, result_id: id(i), start_time: `2023-07-05T00:00:${String(i * 10).padStart(2, '0')}.000`, end_time: `2023-07-05T00:00:${String(i * 10 + 6).padStart(2, '0')}.000`, prediction: i === 1 ? 'Abnormal resistance' : 'Normal' })) };
  }
}
function resolve(item: Stored): Run {
  const elapsed = Date.now() - item.started;
  const status = elapsed < 800 ? 'queued' : elapsed < 2200 ? 'running' : item.fail ? 'failed' : 'completed';
  return { ...item.run, status, results: status === 'completed' ? item.run.results : [], error: status === 'failed' ? { code: 'MOCK_FAILURE', message: 'Development fixture: this recording could not be analysed. Select another file and try again.' } : null } as Run;
}
function csvCell(value: unknown) { return `"${String(value).replaceAll('"', '""')}"`; }
export const mockClient: ApiClient = {
  async createRun(subsystem, files, signal) {
    check(signal);
    const run_id = crypto.randomUUID();
    write([{ run: fixture(subsystem, files, run_id), started: Date.now(), fail: files.some(f => f.name.startsWith('fail-')) }, ...read()]);
    return { run_id, status: 'queued' };
  },
  async getRun(id, signal) {
    check(signal); const item = read().find(item => item.run.run_id === id);
    if (!item) throw new Error('Run not found. Development fixtures are stored in this browser tab.');
    return resolve(item);
  },
  async listRuns(signal) { check(signal); return read().map(item => { const { run_id, subsystem, status } = resolve(item); return { run_id, subsystem, status }; }); },
  async reviewResult(id, status, note, signal) {
    check(signal); const items = read();
    const result = items.flatMap(item => item.run.results as Result[]).find(result => result.result_id === id);
    if (!result) throw new Error('Result not found.');
    result.review_status = status; result.review_note = note; write(items);
    return { review_status: status, review_note: note };
  },
  async exportRun(id, signal) {
    const run = await this.getRun(id, signal);
    if (run.status !== 'completed') throw new Error('Only completed runs can be exported.');
    let rows: unknown[][];
    switch (run.subsystem) {
      case 'door': rows = [['start_time', 'end_time', 'prediction'], ...run.results.map(r => [r.start_time, r.end_time, r.prediction])]; break;
      case 'acv': rows = [['file_id', 'ranked_cars'], ...run.results.map(r => [r.file_id, r.ranked_cars.join('|')])]; break;
      default: rows = [['file_id', 'prediction'], ...run.results.map(r => [r.file_id, r.prediction])];
    }
    return new Blob([rows.map(row => row.map(csvCell).join(',')).join('\r\n') + '\r\n'], { type: 'text/csv' });
  },
  async exportZip() { throw new Error('ZIP export requires the real backend.'); },
};
