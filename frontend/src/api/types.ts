export type Subsystem = 'door' | 'acv' | 'rail' | 'shm';
export type RunStatus = 'queued' | 'running' | 'completed' | 'failed';
export type ReviewStatus = 'unreviewed' | 'confirmed' | 'dismissed' | 'resolved';
export type RailPrediction = 'Normal' | 'Side I' | 'Side II';
export interface Review { review_status: ReviewStatus; review_note: string | null }
export interface ResultBase extends Review { result_id: string }
export interface RailResult extends ResultBase { file_id: string; prediction: RailPrediction }
export interface DoorResult extends ResultBase { start_time: string; end_time: string; prediction: 'Normal' | 'Abnormal resistance' }
export interface AcvResult extends ResultBase { file_id: string; ranked_cars: string[] }
export interface ShmResult extends ResultBase { file_id: string; prediction: number }
export type Result = RailResult | DoorResult | AcvResult | ShmResult;
export interface ChartSeries {
  file_id: string; series_id: string; label: string; unit: string;
  x_kind: 'timestamp' | 'sample_index'; points: { x: string | number; y: number }[];
  car_id?: string; side?: string;
}
// L1 defines newest-first summaries but not timestamp/file-count keys.
// Those columns use session upload metadata until the backend freezes their names.
export interface RunSummary { run_id: string; subsystem: Subsystem; status: RunStatus }
interface RunBase extends RunSummary { chart_series: ChartSeries[]; error: { code: string; message: string } | null }
export type Run = RunBase & (
  { subsystem: 'rail'; results: RailResult[] } |
  { subsystem: 'door'; results: DoorResult[] } |
  { subsystem: 'acv'; results: AcvResult[] } |
  { subsystem: 'shm'; results: ShmResult[] }
);
export interface ApiClient {
  createRun(subsystem: Subsystem, files: File[], signal?: AbortSignal): Promise<Pick<RunSummary, 'run_id' | 'status'>>;
  getRun(id: string, signal?: AbortSignal): Promise<Run>;
  listRuns(signal?: AbortSignal): Promise<RunSummary[]>;
  exportRun(id: string, signal?: AbortSignal): Promise<Blob>;
  reviewResult(id: string, status: ReviewStatus, note: string, signal?: AbortSignal): Promise<Review>;
  exportZip(ids: string[], signal?: AbortSignal): Promise<Blob>;
}
