import type { Run, Subsystem } from '../api/types';
export const subsystems: Subsystem[] = ['door', 'acv', 'rail', 'shm'];
export const config = {
  door: { name: 'Door', description: 'Inspect movement cycles and unusual resistance.', upload: 'Upload a continuous door-controller recording', extension: '.csv', multiple: false },
  acv: { name: 'ACV', description: 'Compare cars to investigate suspected refrigerant leaks.', upload: 'Upload ACV telemetry workbook', extension: '.xlsx', multiple: true },
  rail: { name: 'Rail Corrugation', description: 'Identify corrugation patterns and the affected rail side.', upload: 'Upload axle-box vibration recordings', extension: '.csv', multiple: true },
  shm: { name: 'Structural Health', description: 'Estimate cumulative fatigue damage from stress recordings.', upload: 'Upload structural stress recordings', extension: '.csv', multiple: true },
} as const;
export function summary(run: Run): string {
  switch (run.subsystem) {
    case 'door': { const count = run.results.filter(r => r.prediction === 'Abnormal resistance').length; return `${count} abnormal resistance ${count === 1 ? 'cycle' : 'cycles'}`; }
    case 'rail': return ['Normal', 'Side I', 'Side II'].map(label => `${run.results.filter(r => r.prediction === label).length} ${label}`).join(' / ');
    case 'acv': return run.results.length === 1 ? `Car ${run.results[0].ranked_cars[0] ?? '—'} ranked first` : `${run.results.length} workbooks ranked`;
    case 'shm': return `${run.results.length} ${run.results.length === 1 ? 'file' : 'files'} analysed`;
  }
}
export function saveBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob); const a = document.createElement('a');
  a.href = url; a.download = name; document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export interface UploadMetadata { filenames: string[]; submittedAt: string }
const metadataKey = 'ps3-upload-metadata';
export function rememberUpload(id: string, files: File[]) {
  try {
    const existing = JSON.parse(sessionStorage.getItem(metadataKey) ?? '{}');
    sessionStorage.setItem(metadataKey, JSON.stringify({ ...existing, [id]: { filenames: files.map(f => f.name), submittedAt: new Date().toISOString() } }));
  } catch { /* Session metadata is optional; it never blocks an analysis. */ }
}
export function uploadMetadata(id: string): UploadMetadata | undefined {
  try { return JSON.parse(sessionStorage.getItem(metadataKey) ?? '{}')[id]; } catch { return undefined; }
}
