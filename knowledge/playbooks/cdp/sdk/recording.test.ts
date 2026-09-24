import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import {
  BINDING,
  ChunkAssembler,
  RecordingManager,
  autoRecordingSetting,
  buildPageScript,
  loadRrwebEvents,
  loadRrwebSource,
  resetRrwebSourceCache,
  setAutoRecording,
} from './recording.ts';

type Call = { method: string; params: unknown; opts?: { sessionId?: string } };

const STUB = 'var rrweb = { record: function (opts) { return opts; }, Replayer: function () {} };';

function stubRrweb(home: string): void {
  const path = join(home, 'rrweb-stub.js');
  writeFileSync(path, STUB);
  process.env.CDP_RRWEB_JS = path;
  resetRrwebSourceCache();
}

function mockSession(options: { connected?: boolean; pages?: Array<{ targetId: string; url: string }> } = {}) {
  const calls: Call[] = [];
  const listeners: Array<(method: string, params: unknown, sessionId?: string) => void> = [];
  const pages = options.pages ?? [{ targetId: 't1', url: 'https://example.com/' }];
  const session = {
    isConnected: () => options.connected !== false,
    getActiveSession: () => 'sid-1',
    _call: async (method: string, params: unknown = {}, opts?: { sessionId?: string }) => {
      calls.push({ method, params, opts });
      if (method === 'Target.getTargets') {
        return {
          targetInfos: pages.map(page => ({ type: 'page', title: 'Example', ...page })),
        };
      }
      if (method === 'Target.attachToTarget') return { sessionId: 'sid-1' };
      return {};
    },
    onEvent: (fn: (method: string, params: unknown, sessionId?: string) => void) => {
      listeners.push(fn);
      return () => {
        const index = listeners.indexOf(fn);
        if (index >= 0) listeners.splice(index, 1);
      };
    },
  };
  return { session, calls, listeners };
}

function rrwebEvent(type = 4, timestamp = 1_700_000_000_000): { type: number; timestamp: number; data: { source: number } } {
  return { type, timestamp, data: { source: 0 } };
}

test('recording preference is off by default and persists explicit consent', async () => {
  const home = mkdtempSync(join(tmpdir(), 'browser-harness-js-home-'));
  const previousHome = process.env.BROWSER_HARNESS_JS_HOME;
  const previousOverride = process.env.CDP_RECORD;
  process.env.BROWSER_HARNESS_JS_HOME = home;
  delete process.env.CDP_RECORD;
  try {
    assert.deepEqual(await autoRecordingSetting(), { enabled: false, source: 'default' });
    await setAutoRecording(true);
    assert.deepEqual(await autoRecordingSetting(), { enabled: true, source: 'config' });
    process.env.CDP_RECORD = '0';
    assert.deepEqual(await autoRecordingSetting(), { enabled: false, source: 'CDP_RECORD' });
  } finally {
    if (previousHome == null) delete process.env.BROWSER_HARNESS_JS_HOME;
    else process.env.BROWSER_HARNESS_JS_HOME = previousHome;
    if (previousOverride == null) delete process.env.CDP_RECORD;
    else process.env.CDP_RECORD = previousOverride;
    rmSync(home, { recursive: true, force: true });
  }
});

test('page bootstrap records through the binding and masks inputs', () => {
  const script = buildPageScript('var rrweb = { record: function (opts) { return opts; } };');
  assert.match(script, /maskAllInputs:\s*true/);
  assert.match(script, new RegExp(`window\\.${BINDING}`));
  assert.match(script, /rrweb\.record/);
});

test('chunk assembler rebuilds split rrweb events', () => {
  const event = rrwebEvent(2, 42);
  const json = JSON.stringify(event);
  const assembler = new ChunkAssembler();
  const id = 'a1';
  assert.equal(assembler.push(JSON.stringify({ id, i: 0, n: 2, d: json.slice(0, 12) })), undefined);
  assert.deepEqual(assembler.push(JSON.stringify({ id, i: 1, n: 2, d: json.slice(12) })), event);
});

test('CDP_RRWEB_JS overrides the pinned download', async () => {
  const home = mkdtempSync(join(tmpdir(), 'browser-harness-js-rrweb-override-'));
  const previousHome = process.env.BROWSER_HARNESS_JS_HOME;
  const previousJs = process.env.CDP_RRWEB_JS;
  process.env.BROWSER_HARNESS_JS_HOME = home;
  stubRrweb(home);
  try {
    assert.equal(await loadRrwebSource(), STUB);
  } finally {
    if (previousHome == null) delete process.env.BROWSER_HARNESS_JS_HOME;
    else process.env.BROWSER_HARNESS_JS_HOME = previousHome;
    if (previousJs == null) delete process.env.CDP_RRWEB_JS;
    else process.env.CDP_RRWEB_JS = previousJs;
    resetRrwebSourceCache();
    rmSync(home, { recursive: true, force: true });
  }
});

test('start injects rrweb and persists binding events', async () => {
  const home = mkdtempSync(join(tmpdir(), 'browser-harness-js-rrweb-'));
  const previousHome = process.env.BROWSER_HARNESS_JS_HOME;
  const previousOverride = process.env.CDP_RECORD;
  const previousJs = process.env.CDP_RRWEB_JS;
  process.env.BROWSER_HARNESS_JS_HOME = home;
  delete process.env.CDP_RECORD;
  stubRrweb(home);
  const { session, calls, listeners } = mockSession();
  try {
    const manager = new RecordingManager(session as any);
    const directory = await manager.start('demo', 'Example task');
    const methods = calls.map(call => call.method);
    assert.ok(methods.includes('Target.setAutoAttach'));
    assert.ok(methods.includes('Runtime.addBinding'));
    assert.ok(methods.includes('Page.addScriptToEvaluateOnNewDocument'));
    const injected = calls.find(call => call.method === 'Runtime.evaluate');
    assert.equal((injected?.params as { expression?: string }).expression?.includes('rrweb.record'), true);
    assert.equal((injected?.params as { expression?: string }).expression?.includes('maskAllInputs'), true);
    assert.equal((injected?.params as { expression?: string }).expression?.includes(STUB), true);

    const event = rrwebEvent();
    listeners[0]!('Runtime.bindingCalled', {
      name: BINDING,
      payload: JSON.stringify({ id: 'e', i: 0, n: 1, d: JSON.stringify(event) }),
    }, 'sid-1');
    await manager.stop();

    const grouped = await loadRrwebEvents(directory);
    assert.deepEqual(grouped.get('sid-1'), [event]);
    const disk = readFileSync(join(directory, 'rrweb.jsonl'), 'utf8');
    assert.match(disk, /"sid":"sid-1"/);
    const meta = JSON.parse(readFileSync(join(directory, 'meta.json'), 'utf8'));
    assert.equal(meta.engine, 'rrweb');
    assert.equal(meta.title, 'Example task');
  } finally {
    if (previousHome == null) delete process.env.BROWSER_HARNESS_JS_HOME;
    else process.env.BROWSER_HARNESS_JS_HOME = previousHome;
    if (previousOverride == null) delete process.env.CDP_RECORD;
    else process.env.CDP_RECORD = previousOverride;
    if (previousJs == null) delete process.env.CDP_RRWEB_JS;
    else process.env.CDP_RRWEB_JS = previousJs;
    resetRrwebSourceCache();
    rmSync(home, { recursive: true, force: true });
  }
});

test('start refuses CDP_RECORD=0 and an unconnected session', async () => {
  const home = mkdtempSync(join(tmpdir(), 'browser-harness-js-rrweb-deny-'));
  const previousHome = process.env.BROWSER_HARNESS_JS_HOME;
  const previousOverride = process.env.CDP_RECORD;
  process.env.BROWSER_HARNESS_JS_HOME = home;
  process.env.CDP_RECORD = '0';
  try {
    const connected = mockSession();
    await assert.rejects(() => new RecordingManager(connected.session as any).start('nope'), /CDP_RECORD=0/);
    delete process.env.CDP_RECORD;
    const disconnected = mockSession({ connected: false });
    await assert.rejects(() => new RecordingManager(disconnected.session as any).start('nope'), /not connected/);
  } finally {
    if (previousHome == null) delete process.env.BROWSER_HARNESS_JS_HOME;
    else process.env.BROWSER_HARNESS_JS_HOME = previousHome;
    if (previousOverride == null) delete process.env.CDP_RECORD;
    else process.env.CDP_RECORD = previousOverride;
    rmSync(home, { recursive: true, force: true });
  }
});
