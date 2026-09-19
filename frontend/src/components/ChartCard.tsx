import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { ChartSeries, DoorResult } from '../api/types';
import { withinCycle } from '../utils/timestamps';
export function ChartCard({ series, cycle }: { series: ChartSeries; cycle?: DoorResult }) {
  const points = cycle && series.x_kind === 'timestamp' ? series.points.filter(point => withinCycle(point.x, cycle.start_time, cycle.end_time)) : series.points;
  return <section className="chart-card"><h4>{series.label}{series.car_id ? ` · Car ${series.car_id}` : ''}{series.side ? ` · ${series.side}` : ''}</h4><p className="muted">{series.x_kind === 'timestamp' ? 'Recorded timestamp' : 'Sample index'} · {series.unit || 'Unit not supplied'}{cycle && series.x_kind !== 'timestamp' ? ' · Full recording (cycle alignment unavailable)' : ''}</p>
    {points.length ? <div className="chart" role="img" aria-label={`${series.label}, ${points.length} points. Data table available below.`}><ResponsiveContainer width="100%" height="100%"><LineChart data={points} margin={{ top: 10, right: 15, bottom: 10, left: 5 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="x" minTickGap={50} tick={{ fontSize: 11 }} /><YAxis width={65} tick={{ fontSize: 11 }} /><Tooltip /><Line type="linear" dataKey="y" name={series.label} unit={series.unit ? ` ${series.unit}` : undefined} stroke="#23766a" dot={false} strokeWidth={2} isAnimationActive={false} /></LineChart></ResponsiveContainer></div> : <p>No evidence points available for this cycle.</p>}
    <details><summary>View chart data</summary><div className="table-scroll chart-data"><table><caption className="sr-only">{series.label} source points</caption><thead><tr><th>{series.x_kind === 'timestamp' ? 'Timestamp' : 'Sample index'}</th><th>{series.unit || 'Value'}</th></tr></thead><tbody>{points.map((point, index) => <tr key={index}><td>{point.x}</td><td>{point.y}</td></tr>)}</tbody></table></div></details>
  </section>;
}
