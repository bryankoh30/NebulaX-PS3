import { useEffect, useState } from 'react';
import { api, messageOf } from '../api/client';
import type { ReviewEvent } from '../api/types';
import { ErrorState, StatusBadge } from './States';

export function ReviewHistory({ resultId, version }: { resultId: string; version: number }) {
  const [events, setEvents] = useState<ReviewEvent[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    void api.getReviews(resultId, controller.signal).then(events => {
      if (!controller.signal.aborted) setEvents(events);
    }).catch(error => {
      if (!controller.signal.aborted) setError(messageOf(error));
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [resultId, version, retry]);
  return <section aria-labelledby="review-history-title" className="review-form">
    <h3 id="review-history-title">Review history</h3>
    {loading ? <p role="status">Loading reviews…</p> : error ? <ErrorState message={error} retry={() => setRetry(n => n + 1)} /> : events.length ?
      <ol>{events.map(event => <li key={event.id}><StatusBadge value={event.status} /><time className="cell-note" dateTime={event.created_at}>{event.created_at}</time><p className="saved-note">{event.note || 'No note added.'}</p></li>)}</ol> : <p>No review events recorded.</p>}
  </section>;
}
