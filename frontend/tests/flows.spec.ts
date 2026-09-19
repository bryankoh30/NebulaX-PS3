import { test, expect, type Page } from '@playwright/test';
import type { Run, RunSummary, Subsystem } from '../src/api/types';
import { recordingTimestampKey, withinCycle } from '../src/utils/timestamps';

const review = { review_status: 'unreviewed' as const, review_note: null };
function fixture(subsystem: Subsystem): Run {
  const files = subsystem === 'rail' ? ['recording0.csv', 'recording1.csv', 'recording2.csv'] : [subsystem === 'acv' ? 'case.xlsx' : subsystem === 'shm' ? 'stress.csv' : 'recording.csv'];
  const base = { run_id: `${subsystem}-run`, status: 'completed' as const, error: null, chart_series: [], files, created_at: '2026-09-19T01:00:00+00:00', updated_at: '2026-09-19T01:00:05+00:00' };
  if (subsystem === 'rail') return { ...base, subsystem, results: ['Normal', 'Side I', 'Side II'].map((prediction, i) => ({ ...review, result_id: `r${i}`, file_id: `recording${i}.csv`, prediction })) } as Run;
  if (subsystem === 'door') return { ...base, subsystem, results: ['Normal', 'Abnormal resistance'].map((prediction, i) => ({ ...review, result_id: `d${i}`, start_time: `2023-07-05T00:00:${i}0.000`, end_time: `2023-07-05T00:00:${i}6.000`, prediction })) } as Run;
  if (subsystem === 'acv') return { ...base, subsystem, chart_series: ['03', '09', '02'].map((car_id, index) => ({ file_id: 'case.xlsx', series_id: `car-${car_id}-temperature`, label: `Car ${car_id} cabin temperature`, unit: 'temperature', x_kind: 'sample_index' as const, car_id, points: [{ x: 0, y: 22 + index }, { x: 1, y: 23 + index }] })), results: [{ ...review, result_id: 'a1', file_id: 'case.xlsx', ranked_cars: ['03', '09', '02'] }] };
  return { ...base, subsystem, results: [{ ...review, result_id: 's1', file_id: 'stress.csv', prediction: 0.00482 }] };
}
function runSummary(run: Run): RunSummary {
  const { run_id, status, subsystem, created_at, updated_at, error } = run;
  return { run_id, status, subsystem, created_at, updated_at, error, file_count: run.files.length, result_count: run.results.length };
}
test.beforeEach(async ({ page }) => {
  await page.route('**/api/results/*/reviews', route => route.fulfill({ json: [] }));
});
async function serve(page: Page, subsystem: Subsystem) {
  const run = fixture(subsystem); let polls = 0; const times: number[] = []; let started = 0;
  await page.route('**/api/runs', async route => {
    if (route.request().method() === 'POST') {
      expect(route.request().postDataBuffer()?.toString()).toContain(`name="subsystem"\r\n\r\n${subsystem}`);
      await route.fulfill({ status: 202, json: { run_id: run.run_id, status: 'queued' } });
    } else await route.fulfill({ json: [runSummary(run)] });
  });
  await page.route(`**/api/runs/${run.run_id}`, async route => {
    times.push(Date.now()); polls++; started ||= Date.now();
    const elapsed = Date.now() - started;
    const status = elapsed < 1100 ? 'queued' : elapsed < 2200 ? 'running' : 'completed';
    await route.fulfill({ json: { ...run, status, results: status === 'completed' ? run.results : [] } });
  });
  await page.route(`**/api/runs/${run.run_id}/export`, route => route.fulfill({ contentType: 'text/csv', body: 'file_id,prediction\r\nrecording0.csv,Normal\r\n' }));
  return { run, times, polls: () => polls };
}
async function upload(page: Page, subsystem: Subsystem) {
  await page.goto(`/#/${subsystem}`);
  const names = subsystem === 'rail' ? ['recording0.csv', 'recording1.csv', 'recording2.csv'] : [subsystem === 'acv' ? 'case.xlsx' : subsystem === 'shm' ? 'stress.csv' : 'recording.csv'];
  await page.locator('input[type=file]').setInputFiles(names.map(name => ({ name, mimeType: 'application/octet-stream', buffer: Buffer.from('synthetic browser transport fixture') })));
  await page.getByRole('button', { name: 'Analyse recordings', exact: true }).click();
}
test('Rail upload, polling, filters, details, official export and layout', async ({ page }, testInfo) => {
  const server = await serve(page, 'rail'); await upload(page, 'rail');
  await expect(page.getByText('Queued', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('Analysing recordings', { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Recording results' })).toBeVisible();
  expect(server.times.at(-1)! - server.times.at(-2)!).toBeGreaterThanOrEqual(900);
  await page.getByRole('button', { name: 'Side I', exact: true }).click();
  await expect(page.getByRole('button', { name: 'recording0.csv' })).toHaveCount(0);
  await page.getByRole('button', { name: 'recording1.csv' }).click();
  await expect(page.getByRole('dialog')).toContainText('The model detected a vibration pattern consistent with rail corrugation on Side I.');
  await expect(page.getByRole('dialog')).toContainText('Review Side I and its supporting vibration signal');
  await expect(page.getByRole('dialog').getByRole('heading', { name: 'Signal context' })).toBeVisible();
  await page.getByRole('button', { name: 'Close details' }).click();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download rail_predictions.csv' }).click();
  expect((await download).suggestedFilename()).toBe('rail_predictions.csv');
  const count = server.polls(); await page.waitForTimeout(1200); expect(server.polls()).toBe(count);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.screenshot({ path: testInfo.outputPath('rail-results.png'), fullPage: true });
});
test('Door cycles, contextual causes and review keep predictions unchanged', async ({ page }, testInfo) => {
  await serve(page, 'door'); await upload(page, 'door');
  await expect(page.getByRole('heading', { name: 'Detected cycles' })).toBeVisible();
  await page.getByRole('button', { name: 'Cycle 2' }).click();
  await expect(page.getByRole('dialog')).toContainText('Possible causes to inspect');
  await expect(page.getByRole('dialog')).toContainText('Check the motor-current and door-position traces');
  await page.route('**/api/results/d1/review', async route => {
    expect(route.request().postDataJSON()).toEqual({ status: 'dismissed', note: 'Inspected movement' });
    await route.fulfill({ json: { review_status: 'dismissed', review_note: 'Inspected movement', prediction: 'Normal' } });
  });
  await page.getByLabel('Review status', { exact: true }).selectOption('dismissed');
  await page.getByLabel('Add note').fill('Inspected movement');
  await page.getByRole('button', { name: 'Save review' }).click();
  await expect(page.getByText('Review saved.')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Abnormal resistance detected' })).toBeVisible();
  await page.getByRole('button', { name: 'Close details' }).click();
  await expect(page.getByRole('row').filter({ hasText: 'Cycle 2' })).toContainText('Abnormal resistance');
  await expect(page.getByRole('row').filter({ hasText: 'Cycle 2' })).toContainText('dismissed');
  await page.screenshot({ path: testInfo.outputPath('door-results.png'), fullPage: true });
});
for (const subsystem of ['acv', 'shm'] as const) test(`${subsystem} displays its own result semantics`, async ({ page }, testInfo) => {
  await serve(page, subsystem); await upload(page, subsystem);
  await expect(page.getByRole('heading', { name: 'Recording results' })).toBeVisible();
  await page.getByRole('button', { name: subsystem === 'acv' ? 'case.xlsx' : 'stress.csv' }).click();
  const dialog = page.getByRole('dialog');
  if (subsystem === 'acv') {
    await expect(dialog.locator('ol li')).toHaveText(['Car 03', 'Car 09', 'Car 02']);
    await expect(dialog).toContainText('The ranking compares each car');
    await expect(dialog).toContainText('Prioritise Car 03 for inspection');
    await expect(dialog.getByRole('heading', { name: 'Cabin temperature across peer cars' })).toBeVisible();
    await expect(dialog).toContainText('Top-ranked: Car 03');
    await expect(dialog.locator('.acv-comparison')).toHaveCount(1);
    await expect(dialog.locator('.chart-card')).toHaveCount(1);
  } else {
    await expect(dialog).toContainText('0.00482');
    await expect(dialog).toContainText('cumulative fatigue damage from the supplied stress recording');
    await expect(dialog).toContainText("operator's approved engineering limits and procedures");
    await expect(dialog).toContainText('not a safety classification, failure probability, or remaining-life estimate');
  }
  await page.screenshot({ path: testInfo.outputPath(`${subsystem}-details.png`), fullPage: true });
});
test('upload validation and multi-file controls', async ({ page }) => {
  const file = (name: string) => ({ name, mimeType: 'text/csv', buffer: Buffer.from('x,y\n1,2') });
  await page.goto('/#/door');
  await expect(page.locator('input[type=file]')).not.toHaveAttribute('multiple');
  await page.locator('input[type=file]').setInputFiles(file('wrong.xlsx'));
  await expect(page.getByRole('alert')).toContainText('Select .CSV');
  await page.locator('input[type=file]').setInputFiles(file('recording.csv'));
  await expect(page.getByText('1 file selected', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Remove recording.csv' }).click();
  await expect(page.getByRole('button', { name: 'Analyse recordings' })).toBeDisabled();
  for (const subsystem of ['rail', 'shm']) {
    await page.goto(`/#/${subsystem}`);
    await page.locator('input[type=file]').setInputFiles([file('one.csv'), file('two.csv')]);
    await expect(page.getByText('2 files selected', { exact: true })).toBeVisible();
  }
  await page.goto('/#/acv'); await expect(page.locator('input[type=file]')).toHaveAttribute('accept', '.xlsx');
});
test('polling stops on failure and navigation; failure message is readable', async ({ page }) => {
  let count = 0;
  await page.route('**/api/runs/failure', async route => { count++; await route.fulfill({ json: { ...fixture('rail'), run_id: 'failure', status: 'failed', results: [], error: { code: 'MISSING_ARTIFACT', message: 'Rail model artifact is unavailable.' } } }); });
  await page.goto('/#/rail?run=failure'); await expect(page.getByRole('alert')).toContainText('Rail model artifact is unavailable.');
  const afterFailure = count; await page.waitForTimeout(1200); expect(count).toBe(afterFailure);
  await page.route('**/api/runs/pending', async route => { count++; await route.fulfill({ json: { ...fixture('rail'), run_id: 'pending', status: 'running', results: [] } }); });
  await page.goto('/#/rail?run=pending'); await expect(page.getByText('Analysing recordings').first()).toBeVisible();
  await page.goto('/#/shm'); const afterNavigation = count; await page.waitForTimeout(1300); expect(count).toBe(afterNavigation);
});
test('Overview, history, refresh, reopening and ZIP request', async ({ page }, testInfo) => {
  const runs = (['door', 'acv', 'rail', 'shm'] as const).map(fixture);
  await page.route('**/api/runs', route => route.fulfill({ json: runs.map(runSummary) }));
  for (const run of runs) await page.route(`**/api/runs/${run.run_id}`, route => route.fulfill({ json: run }));
  await page.goto('/#/overview');
  await expect(page.getByRole('heading', { name: 'Review queue' })).toBeVisible();
  await expect(page.getByText('1 abnormal resistance cycle', { exact: true })).toBeVisible();
  await expect(page.getByText('Car 03 ranked first', { exact: true }).first()).toBeVisible();
  const firstFinding = page.locator('tbody tr').first();
  await expect(firstFinding).toContainText('Abnormal resistance');
  await expect(firstFinding).toContainText('Needs review');
  await page.screenshot({ path: testInfo.outputPath('overview.png'), fullPage: true });
  await page.goto('/#/history');
  await expect(page.getByRole('link', { name: 'Open results' })).toHaveCount(4);
  await page.screenshot({ path: testInfo.outputPath('history.png'), fullPage: true });
  for (const check of await page.getByRole('checkbox').all()) await check.check();
  await page.route('**/api/exports', async route => { expect(route.request().postDataJSON().run_ids).toHaveLength(4); await route.fulfill({ contentType: 'application/zip', body: 'transport fixture' }); });
  const downloaded = page.waitForEvent('download'); await page.getByRole('button', { name: 'Download predictions.zip' }).click();
  expect((await downloaded).suggestedFilename()).toBe('predictions.zip');
  await page.getByRole('link', { name: 'Open results' }).first().click(); await page.reload();
  await expect(page.getByRole('heading', { name: 'Detected cycles' })).toBeVisible();
});
test('API errors do not silently fall back to fake results', async ({ page }) => {
  await page.route('**/api/runs', route => route.fulfill({ status: 503, json: { error: { code: 'OFFLINE', message: 'Worker is offline.' } } }));
  await page.goto('/#/overview'); await expect(page.getByRole('alert')).toContainText('Worker is offline.');
  await expect(page.getByText('Development only', { exact: false })).toHaveCount(0);
  await page.getByRole('button', { name: 'Try again' }).click(); await expect(page.getByRole('alert')).toContainText('Worker is offline.');
});
test('signal context renders only returned series', async ({ page }) => {
  const run = fixture('rail'); run.chart_series = [{ file_id: 'recording1.csv', series_id: 'side-i', label: 'Side I aggregated vibration', unit: 'm/s²', x_kind: 'sample_index', side: 'Side I', points: [{ x: 0, y: 1 }, { x: 1, y: 2 }] }];
  await page.route('**/api/runs/rail-run', route => route.fulfill({ json: run }));
  await page.goto('/#/rail?run=rail-run'); await page.getByRole('button', { name: 'recording1.csv' }).click();
  await expect(page.getByRole('button', { name: 'Close details' })).toBeFocused();
  await expect(page.getByRole('heading', { name: 'Signal context' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Side I aggregated vibration · Side I' })).toBeVisible();
  await page.getByText('View chart data', { exact: true }).click();
  await expect(page.getByRole('dialog').getByRole('table')).toContainText('Sample index');
  await page.keyboard.press('Escape'); await expect(page.getByRole('dialog')).toHaveCount(0);
});
test('navigation exposes all four subsystems on desktop and mobile', async ({ page }, testInfo) => {
  await page.goto('/#/rail');
  if (testInfo.project.name === 'mobile') await page.getByRole('button', { name: 'Open navigation' }).click();
  const nav = page.getByRole('navigation', { name: 'Main navigation' });
  for (const name of ['Door', 'ACV', 'Rail Corrugation', 'Structural Health']) await expect(nav.getByRole('link', { name, exact: true })).toBeVisible();
  await nav.getByRole('link', { name: 'Structural Health' }).click();
  await expect(page.getByRole('heading', { name: 'Structural Health', exact: true })).toBeVisible();
  if (testInfo.project.name === 'mobile') await expect(page.getByRole('button', { name: 'Open navigation' })).toHaveAttribute('aria-expanded', 'false');
});
test('separate development adapter models all run types and fixture failures', async ({ page }) => {
  await page.goto('/#/rail'); await page.clock.install();
  const ids = await page.evaluate(async path => {
    const { mockClient } = await import(path);
    const created = [];
    for (const subsystem of ['rail', 'door', 'acv', 'shm']) {
      const file = new File(['fixture'], subsystem === 'acv' ? 'case.xlsx' : 'recording.csv');
      created.push(await mockClient.createRun(subsystem, [file]));
    }
    const failed = await mockClient.createRun('rail', [new File(['fixture'], 'fail-recording.csv')]);
    return { created, failed };
  }, '/src/api/mockClient.ts');
  expect(ids.created.every(run => run.status === 'queued')).toBeTruthy();
  await page.clock.fastForward(2500);
  const results = await page.evaluate(async ({ ids, path }) => {
    const { mockClient } = await import(path);
    return {
      runs: await Promise.all(ids.created.map((r: { run_id: string }) => mockClient.getRun(r.run_id))),
      failed: await mockClient.getRun(ids.failed.run_id),
      csv: await (await mockClient.exportRun(ids.created[2].run_id)).text(),
    };
  }, { ids, path: '/src/api/mockClient.ts' });
  expect(results.runs.every((run: Run) => run.status === 'completed')).toBeTruthy();
  expect(results.failed.status).toBe('failed');
  expect(results.csv).toContain('03|05|02');
});

test('recording timestamps compare chronologically across legacy and ISO formats', () => {
  expect(withinCycle('2023-7-5-0-0-10-0', '2023-7-5-0-0-9-0', '2023-7-5-0-0-12-0')).toBe(true);
  expect(withinCycle('2023-07-05T00:01:00.001', '2023-7-5-0-0-59-999', '2023-7-5-0-1-0-20')).toBe(true);
  expect(withinCycle('2024-01-01T00:00:00.000', '2023-12-31-23-59-59-999', '2024-1-1-0-0-1-0')).toBe(true);
  expect(withinCycle('2023-7-5-0-0-8-999', '2023-07-05T00:00:09.000', '2023-07-05T00:00:12.000')).toBe(false);
  expect(recordingTimestampKey('2023-7-5-0-0-9-20')).toBe(recordingTimestampKey('2023-07-05T00:00:09.020'));
  expect(recordingTimestampKey('2023-02-29T00:00:00')).toBeNull();
  expect(recordingTimestampKey('2024-02-29T00:00:00')).not.toBeNull();
  expect(withinCycle('invalid', '2023-7-5-0-0-9-0', '2023-7-5-0-0-12-0')).toBe(false);
});

test('legacy Door cycle chart retains valid points and excludes adjacent cycles', async ({ page }) => {
  const run = fixture('door');
  if (run.subsystem !== 'door') throw new Error('Wrong fixture');
  run.results[0].start_time = '2023-7-5-0-0-9-0'; run.results[0].end_time = '2023-7-5-0-0-12-0';
  run.chart_series = [{ file_id: 'recording.csv', series_id: 'current', label: 'Motor current', unit: 'mA', x_kind: 'timestamp', points: [
    { x: '2023-7-5-0-0-8-0', y: 999 }, { x: '2023-7-5-0-0-10-0', y: 123 }, { x: '2023-07-05T00:00:11.000', y: 456 }, { x: '2023-7-5-0-0-13-0', y: 888 },
  ] }];
  await page.route('**/api/runs/door-run', route => route.fulfill({ json: run }));
  await page.goto('/#/door?run=door-run'); await page.getByRole('button', { name: 'Cycle 1' }).click();
  await page.getByText('View chart data', { exact: true }).click();
  const table = page.getByRole('dialog').getByRole('table');
  await expect(table.getByRole('row')).toHaveCount(3);
  await expect(table).toContainText('123'); await expect(table).toContainText('456');
  await expect(table).not.toContainText('999'); await expect(table).not.toContainText('888');
});

test('history uses persisted API metadata in a fresh browser session', async ({ page }) => {
  const run = fixture('rail');
  await page.route('**/api/runs', route => route.fulfill({ json: [runSummary(run)] }));
  await page.goto('/#/history');
  const row = page.getByRole('row').filter({ hasText: 'Rail Corrugation' });
  await expect(row.getByRole('cell').nth(2)).toHaveText('3');
  await expect(row).toContainText(run.created_at);
  await expect(row).toContainText('3 results');
  await page.reload(); await expect(row).toContainText(run.created_at);
  await expect(page.getByText('Unavailable', { exact: true })).toHaveCount(0);
});

test('review history loads and refreshes after saving metadata', async ({ page }) => {
  const run = fixture('door'); let saved = false;
  await page.route('**/api/runs/door-run', route => route.fulfill({ json: run }));
  await page.route('**/api/results/d0/reviews', route => route.fulfill({ json: saved ? [{ id: 'event', status: 'confirmed', note: 'Checked cycle', created_at: '2026-09-19T02:00:00+00:00' }] : [] }));
  await page.route('**/api/results/d0/review', route => { saved = true; return route.fulfill({ json: { ...run.results[0], review_status: 'confirmed', review_note: 'Checked cycle' } }); });
  await page.goto('/#/door?run=door-run'); await page.getByRole('button', { name: 'Cycle 1' }).click();
  await expect(page.getByText('No review events recorded.')).toBeVisible();
  await expect(page.getByLabel('Add note')).toHaveAttribute('maxlength', '2000');
  await page.getByLabel('Review status', { exact: true }).selectOption('confirmed');
  await page.getByLabel('Add note').fill('Checked cycle'); await page.getByRole('button', { name: 'Save review' }).click();
  const history = page.getByRole('region', { name: 'Review history' });
  await expect(history).toContainText('Checked cycle'); await expect(history).toContainText('2026-09-19T02:00:00+00:00');
});

test('case-insensitive duplicate uploads match backend validation', async ({ page }) => {
  await page.goto('/#/rail');
  await page.locator('input[type=file]').setInputFiles(['sample.csv', 'SAMPLE.csv'].map(name => ({ name, mimeType: 'text/csv', buffer: Buffer.from('synthetic') })));
  await expect(page.getByRole('alert')).toContainText('ignoring case');
  await expect(page.getByRole('button', { name: 'Analyse recordings' })).toBeDisabled();
});

test('validation and missing-model errors remain readable', async ({ page }) => {
  await page.route('**/api/runs', route => route.fulfill({ status: 422, json: { detail: [{ loc: ['body', 'files'], msg: 'Field required' }] } }));
  await upload(page, 'shm');
  await expect(page.getByRole('alert')).toContainText('files: Field required');
  await page.route('**/api/runs/unavailable', route => route.fulfill({ json: { ...fixture('shm'), status: 'failed', results: [], error: { code: 'model_unavailable', message: 'SHM analysis is unavailable because its model artifact is not installed.' } } }));
  await page.goto('/#/shm?run=unavailable');
  await expect(page.getByRole('alert')).toContainText('model artifact is not installed');
  await expect(page.getByRole('button', { name: 'Download shm_predictions.csv' })).toHaveCount(0);
});
