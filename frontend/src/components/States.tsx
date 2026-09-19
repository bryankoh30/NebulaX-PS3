import { AlertCircle, CircleCheck, LoaderCircle, ScanLine } from 'lucide-react';
import type { RunStatus } from '../api/types';
export const statusText: Record<RunStatus, string> = { queued: 'Queued', running: 'Analysing recordings', completed: 'Completed', failed: 'Analysis failed' };
export function StatusBadge({ value }: { value: string }) {
  const tone = value === 'Normal' || value === 'completed' || value === 'resolved' ? 'good' : ['Side I', 'Side II', 'Abnormal resistance', 'failed'].includes(value) ? 'attention' : 'neutral';
  return <span className={`badge ${tone}`}>{tone === 'good' ? <CircleCheck size={13} /> : <span className="badge-dot" />}{statusText[value as RunStatus] ?? value}</span>;
}
export function LoadingState({ text = 'Loading recordings…' }: { text?: string }) { return <div className="state compact" role="status"><LoaderCircle className="spin" size={22} /><span>{text}</span></div>; }
export function ErrorState({ message, retry }: { message: string; retry?: () => void }) { return <div className="error" role="alert"><AlertCircle size={20} /><div><strong>Unable to complete this step</strong><p>{message}</p>{retry && <button className="secondary" onClick={retry}>Try again</button>}</div></div>; }
export function EmptyState({ title = 'No recordings analysed yet', text = 'Upload recordings to see model findings and supporting evidence.' }: { title?: string; text?: string }) { return <div className="state"><ScanLine size={32} /><h3>{title}</h3><p>{text}</p></div>; }
