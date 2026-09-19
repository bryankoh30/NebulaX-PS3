// Compare recording wall-clock values without assigning a browser timezone.
// Older persisted Door runs use YYYY-M-D-H-M-S-ms; new runs use ISO.
export function recordingTimestampKey(value: string | number): string | null {
  if (typeof value !== 'string') return null;
  const source = /^(\d{4})-(\d{1,2})-(\d{1,2})-(\d{1,2})-(\d{1,2})-(\d{1,2})-(\d{1,3})$/.exec(value);
  const iso = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?$/.exec(value);
  const match = source ?? iso;
  if (!match) return null;
  const [year, month, day, hour, minute, second] = match.slice(1, 7).map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (year < 1 || month < 1 || month > 12 || day < 1 || day > days[month - 1] || hour > 23 || minute > 59 || second > 59) return null;
  const fraction = source ? match[7].padStart(3, '0').padEnd(6, '0') : (match[7] ?? '').padEnd(6, '0');
  return `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}T${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}:${String(second).padStart(2, '0')}.${fraction}`;
}
export function withinCycle(value: string | number, start: string, end: string): boolean {
  const point = recordingTimestampKey(value), first = recordingTimestampKey(start), last = recordingTimestampKey(end);
  return point !== null && first !== null && last !== null && point >= first && point <= last;
}
