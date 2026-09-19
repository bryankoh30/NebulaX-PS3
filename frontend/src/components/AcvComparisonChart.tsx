import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { ChartSeries } from '../api/types';

type ComparisonRow = { x: string | number } & Record<string, string | number>;

function valueKey(carId: string) {
  return `car_${carId.replace(/[^a-zA-Z0-9]/g, '_')}`;
}

export function AcvComparisonChart({ series, rankedCars }: { series: ChartSeries[]; rankedCars: string[] }) {
  const byCar = new Map(series.filter(item => item.car_id).map(item => [item.car_id!, item]));
  const cars = [...rankedCars.filter(car => byCar.has(car)), ...[...byCar.keys()].filter(car => !rankedCars.includes(car))];
  const topCar = rankedCars[0];
  const rows = new Map<string, ComparisonRow>();
  for (const car of cars) {
    for (const point of byCar.get(car)?.points ?? []) {
      const key = `${typeof point.x}:${String(point.x)}`;
      const row = rows.get(key) ?? { x: point.x };
      row[valueKey(car)] = point.y;
      rows.set(key, row);
    }
  }
  const data = [...rows.values()];
  const source = cars.length ? byCar.get(cars[0]) : undefined;
  const unit = source?.unit || 'Unit not supplied';
  const xLabel = source?.x_kind === 'timestamp' ? 'Recorded timestamp' : 'Sample index';
  if (!cars.length || !data.length) return <p className="evidence-empty">No comparable car-temperature series was supplied.</p>;

  return <section className="chart-card acv-comparison">
    <div className="comparison-heading"><div><h4>Cabin temperature across peer cars</h4><p className="muted">{xLabel} · {unit} · backend-provided values</p></div><strong>Top-ranked: Car {topCar}</strong></div>
    <div className="chart comparison-chart" role="img" aria-label={`Car ${topCar} highlighted against ${cars.length - 1} peer cars. Data table available below.`}>
      <ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ top: 10, right: 15, bottom: 10, left: 5 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="x" minTickGap={50} tick={{ fontSize: 11 }} /><YAxis width={65} tick={{ fontSize: 11 }} /><Tooltip /><Legend />{cars.map(car => <Line key={car} type="linear" dataKey={valueKey(car)} name={`Car ${car}`} unit={source?.unit ? ` ${source.unit}` : undefined} stroke={car === topCar ? '#176957' : '#a9b5ae'} strokeWidth={car === topCar ? 3 : 1.25} strokeOpacity={car === topCar ? 1 : .72} dot={false} isAnimationActive={false} />)}</LineChart></ResponsiveContainer>
    </div>
    <details><summary>View comparison data</summary><div className="table-scroll chart-data"><table><caption className="sr-only">ACV peer-car comparison source points</caption><thead><tr><th>{xLabel}</th>{cars.map(car => <th key={car}>Car {car}{car === topCar ? ' (top-ranked)' : ''}</th>)}</tr></thead><tbody>{data.map((row, index) => <tr key={index}><td>{row.x}</td>{cars.map(car => <td key={car}>{row[valueKey(car)] ?? '—'}</td>)}</tr>)}</tbody></table></div></details>
  </section>;
}
