/**
 * Consent-based rrweb session recording.
 *
 * Recording is off by default. startRecording() downloads a pinned rrweb UMD
 * into ~/.browser-harness-js (checksummed, cached) and injects rrweb.record
 * into every page target, then appends one JSON line per rrweb event. Replay
 * is the rrweb Replayer, not a screenshot video compiler.
 */

import { createHash } from 'node:crypto';
import { appendFile, chmod, mkdir, readFile, readdir, rename, stat, unlink, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { createServer } from 'node:http';
import { homedir } from 'node:os';
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { pathToFileURL } from 'node:url';
import type { Session } from './session.ts';

type JsonObject = Record<string, unknown>;

type RecordingMeta = {
  name: string;
  title: string | null;
  started: number;
  engine: 'rrweb';
};

type ChunkMessage = {
  id: string;
  i: number;
  n: number;
  d: string;
};

type StoredEvent = {
  sid: string;
  e: JsonObject;
};

type PageTargetInfo = {
  targetId?: string;
  type?: string;
  url?: string;
  title?: string;
};

export const BINDING = '__bh_rrweb';
export const EVENTS_FILE = 'rrweb.jsonl';
export const RRWEB_VERSION = '2.1.1';
export const RRWEB_URL = `https://cdn.jsdelivr.net/npm/rrweb@${RRWEB_VERSION}/dist/rrweb.umd.min.cjs`;
export const RRWEB_SHA256 = '26dcba7afcf8b8ab08281acbb788b55c64103a511004769ba03539ee16cd2ecc';
const CHUNK_LIMIT = 24 * 1024;
const MAX_CHUNKS = 512;
const SKIP_URL = /^(chrome|devtools|chrome-extension):/i;

const REPLAY_URL = new URL('./rrweb-replay.html', import.meta.url);

let pageScriptCache: string | undefined;
let pageScriptInFlight: Promise<string> | undefined;

export function recordingHome(): string {
  const configured = process.env.BROWSER_HARNESS_JS_HOME;
  return resolve(configured || join(homedir(), '.browser-harness-js'));
}

export function recordingsRoot(): string {
  return resolve(process.env.CDP_RECORDINGS_DIR || join(recordingHome(), 'recordings'));
}

function configPath(): string {
  return join(recordingHome(), 'recording.json');
}

function markerPath(): string {
  const port = process.env.CDP_REPL_PORT || '9876';
  return join(recordingsRoot(), `.active-${port}`);
}

function eventsPath(directory: string): string {
  return join(directory, EVENTS_FILE);
}

function envOverride(): boolean | undefined {
  const raw = process.env.CDP_RECORD;
  if (raw == null) return undefined;
  return !['0', 'false', 'no', 'off'].includes(raw.trim().toLowerCase());
}

async function loadConfig(): Promise<JsonObject> {
  try {
    const value: unknown = JSON.parse(await readFile(configPath(), 'utf8'));
    return value && typeof value === 'object' && !Array.isArray(value) ? value as JsonObject : {};
  } catch {
    return {};
  }
}

export async function autoRecordingSetting(): Promise<{ enabled: boolean; source: 'CDP_RECORD' | 'config' | 'default' }> {
  const override = envOverride();
  if (override !== undefined) return { enabled: override, source: 'CDP_RECORD' };
  const config = await loadConfig();
  if (typeof config.enabled === 'boolean') return { enabled: config.enabled, source: 'config' };
  return { enabled: false, source: 'default' };
}

export async function setAutoRecording(enabled: boolean): Promise<void> {
  await mkdir(recordingHome(), { recursive: true, mode: 0o700 });
  const target = configPath();
  const temporary = `${target}.${process.pid}.tmp`;
  await writeFile(temporary, JSON.stringify({ enabled }) + '\n', { mode: 0o600 });
  await rename(temporary, target);
  if (process.platform !== 'win32') await chmod(target, 0o600);
}

export async function activeRecording(): Promise<string | undefined> {
  try {
    const candidate = resolve((await readFile(markerPath(), 'utf8')).trim());
    const root = recordingsRoot();
    const child = relative(root, candidate);
    if (child === '..' || child.startsWith('..' + sep) || isAbsolute(child)) return undefined;
    if (!(await stat(candidate)).isDirectory()) return undefined;
    return candidate;
  } catch {
    return undefined;
  }
}

export async function listRecordings(): Promise<string[]> {
  const root = recordingsRoot();
  let names: string[];
  try { names = await readdir(root); } catch { return []; }
  const found: Array<{ path: string; modified: number }> = [];
  await Promise.all(names.filter(name => !name.startsWith('.')).map(async name => {
    const path = join(root, name);
    try {
      if (!(await stat(path)).isDirectory()) return;
      const evidence = join(path, EVENTS_FILE);
      const modified = await stat(existsSync(evidence) ? evidence : path);
      if (existsSync(join(path, 'meta.json')) || existsSync(evidence)) {
        found.push({ path, modified: modified.mtimeMs });
      }
    } catch { /* Ignore concurrent deletion and unreadable directories. */ }
  }));
  return found.sort((a, b) => b.modified - a.modified).map(item => item.path);
}

export async function latestRecording(): Promise<string | undefined> {
  return (await listRecordings())[0];
}

function safeName(name?: string): string {
  const fallback = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+/, '').replace('T', '-');
  const value = (name || `rec-${fallback}`).trim();
  if (!value || value === '.' || value === '..' || /[/\\]/.test(value)) {
    throw new Error('recording name must be one safe path component');
  }
  const normalized = value.replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/^-+|-+$/g, '');
  if (!normalized) throw new Error('recording name contains no usable characters');
  return normalized;
}

async function writePrivateJson(path: string, value: unknown): Promise<void> {
  await writeFile(path, JSON.stringify(value, null, 2) + '\n', { mode: 0o600 });
}

async function createRecording(name: string, title: string | undefined): Promise<string> {
  const root = recordingsRoot();
  await mkdir(root, { recursive: true, mode: 0o700 });
  let candidate = safeName(name);
  let directory = join(root, candidate);
  let suffix = 2;
  while (existsSync(directory)) {
    candidate = `${safeName(name)}-${suffix++}`;
    directory = join(root, candidate);
  }
  await mkdir(directory, { mode: 0o700 });
  const meta: RecordingMeta = {
    name: basename(directory),
    title: title?.trim() || null,
    started: Date.now() / 1000,
    engine: 'rrweb',
  };
  await writePrivateJson(join(directory, 'meta.json'), meta);
  await writeFile(markerPath(), directory, { mode: 0o600 });
  return directory;
}

function isRrwebEvent(value: unknown): value is JsonObject {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const event = value as JsonObject;
  return typeof event.type === 'number' && typeof event.timestamp === 'number';
}

export class ChunkAssembler {
  private pending = new Map<string, { n: number; parts: Array<string | undefined>; got: number }>();

  push(payload: string): JsonObject | undefined {
    let message: ChunkMessage;
    try {
      const value: unknown = JSON.parse(payload);
      if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined;
      const raw = value as JsonObject;
      if (typeof raw.id !== 'string' || typeof raw.i !== 'number' || typeof raw.n !== 'number' || typeof raw.d !== 'string') {
        return undefined;
      }
      message = { id: raw.id, i: raw.i, n: raw.n, d: raw.d };
    } catch {
      return undefined;
    }
    if (!Number.isInteger(message.i) || !Number.isInteger(message.n)) return undefined;
    if (message.n < 1 || message.n > MAX_CHUNKS || message.i < 0 || message.i >= message.n) return undefined;
    if (message.d.length > CHUNK_LIMIT + 1024) return undefined;
    if (message.n === 1) return parseEventJson(message.d);
    let entry = this.pending.get(message.id);
    if (!entry) {
      entry = { n: message.n, parts: Array.from({ length: message.n }), got: 0 };
      this.pending.set(message.id, entry);
    } else if (entry.n !== message.n) {
      this.pending.delete(message.id);
      return undefined;
    }
    if (entry.parts[message.i] != null) return undefined;
    entry.parts[message.i] = message.d;
    entry.got += 1;
    if (entry.got !== entry.n) return undefined;
    this.pending.delete(message.id);
    return parseEventJson(entry.parts.join(''));
  }
}

function parseEventJson(json: string): JsonObject | undefined {
  try {
    const value: unknown = JSON.parse(json);
    return isRrwebEvent(value) ? value : undefined;
  } catch {
    return undefined;
  }
}

export function buildPageScript(vendorSource: string): string {
  return `;(function () {
  if (window.__bh_rrweb_on) return;
  ${vendorSource}
  var rrweb = window.rrweb || rrweb;
  if (!rrweb || typeof rrweb.record !== 'function') return;
  if (typeof window.${BINDING} !== 'function') return;
  window.__bh_rrweb_on = 1;
  var seq = 0;
  var CHUNK = ${CHUNK_LIMIT};
  function emit(event) {
    try {
      var json = JSON.stringify(event);
      var id = (++seq).toString(36) + '-' + Date.now().toString(36);
      var n = Math.max(1, Math.ceil(json.length / CHUNK));
      for (var i = 0; i < n; i++) {
        window.${BINDING}(JSON.stringify({
          id: id,
          i: i,
          n: n,
          d: json.slice(i * CHUNK, (i + 1) * CHUNK)
        }));
      }
    } catch (err) {}
  }
  try {
    window.__bh_rrweb_stop = rrweb.record({
      emit: emit,
      maskAllInputs: true,
      maskInputOptions: { password: true },
      recordCanvas: false,
      collectFonts: false,
      sampling: { mousemove: 50, scroll: 150, input: 'last' }
    });
  } catch (err) {
    window.__bh_rrweb_on = 0;
  }
})();`;
}

function rrwebCachePath(): string {
  return join(recordingHome(), 'cache', `rrweb-${RRWEB_VERSION}.min.js`);
}

function sha256Hex(value: string | Buffer): string {
  return createHash('sha256').update(value).digest('hex');
}

export function resetRrwebSourceCache(): void {
  pageScriptCache = undefined;
  pageScriptInFlight = undefined;
}

export async function loadRrwebSource(): Promise<string> {
  const override = process.env.CDP_RRWEB_JS;
  if (override) return await readFile(resolve(override), 'utf8');
  const cached = rrwebCachePath();
  try {
    const existing = await readFile(cached);
    if (sha256Hex(existing) === RRWEB_SHA256) return existing.toString('utf8');
  } catch { /* miss or unreadable */ }
  let body: Buffer;
  try {
    const response = await fetch(RRWEB_URL);
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    body = Buffer.from(await response.arrayBuffer());
  } catch (error) {
    throw new Error(
      `rrweb ${RRWEB_VERSION} is not cached at ${cached} and download failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  if (sha256Hex(body) !== RRWEB_SHA256) {
    throw new Error(`rrweb ${RRWEB_VERSION} checksum mismatch (expected ${RRWEB_SHA256})`);
  }
  await mkdir(dirname(cached), { recursive: true, mode: 0o700 });
  const temporary = `${cached}.${process.pid}.tmp`;
  await writeFile(temporary, body, { mode: 0o600 });
  await rename(temporary, cached);
  if (process.platform !== 'win32') await chmod(cached, 0o600);
  return body.toString('utf8');
}

async function pageScript(): Promise<string> {
  if (pageScriptCache) return pageScriptCache;
  if (!pageScriptInFlight) {
    pageScriptInFlight = loadRrwebSource().then(source => {
      pageScriptCache = buildPageScript(source);
      return pageScriptCache;
    }).finally(() => { pageScriptInFlight = undefined; });
  }
  return pageScriptInFlight;
}

function skipUrl(url: string | undefined): boolean {
  return !!url && SKIP_URL.test(url);
}

export async function loadRrwebEvents(directory: string): Promise<Map<string, JsonObject[]>> {
  const grouped = new Map<string, JsonObject[]>();
  let text = '';
  try { text = await readFile(eventsPath(directory), 'utf8'); } catch { return grouped; }
  for (const line of text.split('\n')) {
    if (!line.trim()) continue;
    try {
      const value: unknown = JSON.parse(line);
      if (!value || typeof value !== 'object' || Array.isArray(value)) continue;
      const row = value as StoredEvent;
      if (typeof row.sid !== 'string' || !isRrwebEvent(row.e)) continue;
      const list = grouped.get(row.sid) ?? [];
      list.push(row.e);
      grouped.set(row.sid, list);
    } catch { /* skip malformed lines */ }
  }
  return grouped;
}

export class RecordingManager {
  private session: Session;
  private directory: string | undefined;
  private unsub: (() => void) | undefined;
  private instrumented = new Set<string>();
  private assembler = new ChunkAssembler();
  private queue: Promise<void> = Promise.resolve();
  private instrumentQueue: Promise<void> = Promise.resolve();
  private startInFlight = false;

  constructor(session: Session) {
    this.session = session;
  }

  async start(name?: string, title?: string): Promise<string> {
    if (envOverride() === false) throw new Error('recording disabled by CDP_RECORD=0');
    if (this.startInFlight) throw new Error('another recording start is already in progress');
    if (!this.session.isConnected()) throw new Error('not connected. Call session.connect() first');
    if (this.unsub) throw new Error(`recording already active: ${this.directory}`);
    this.startInFlight = true;
    try {
      await pageScript();
      const stale = await activeRecording();
      if (stale) await unlink(markerPath()).catch(() => {});
      const directory = await createRecording(safeName(name), title);
      this.directory = directory;
      this.instrumented.clear();
      this.assembler = new ChunkAssembler();
      this.unsub = this.session.onEvent(this.onCdpEvent);
      await this.session._call('Target.setDiscoverTargets', { discover: true });
      await this.session._call('Target.setAutoAttach', {
        autoAttach: true,
        waitForDebuggerOnStart: false,
        flatten: true,
      });
      await this.attachExisting();
      return directory;
    } catch (error) {
      this.unsub?.();
      this.unsub = undefined;
      this.directory = undefined;
      await unlink(markerPath()).catch(() => {});
      throw error;
    } finally {
      this.startInFlight = false;
    }
  }

  async stop(): Promise<string | undefined> {
    const directory = this.directory ?? await activeRecording();
    this.unsub?.();
    this.unsub = undefined;
    const sessionIds = [...this.instrumented];
    this.instrumented.clear();
    await Promise.all(sessionIds.map(sessionId => this.session._call('Runtime.evaluate', {
      expression: 'try { if (typeof window.__bh_rrweb_stop === "function") window.__bh_rrweb_stop(); window.__bh_rrweb_on = 0; } catch (e) {}',
    }, { sessionId }).catch(() => {})));
    await this.flush();
    await unlink(markerPath()).catch(() => {});
    this.directory = undefined;
    return directory;
  }

  async status(): Promise<{ enabled: boolean; source: string; active?: string; latest?: string; engine: 'rrweb' }> {
    const setting = await autoRecordingSetting();
    return {
      ...setting,
      active: this.directory ?? await activeRecording(),
      latest: await latestRecording(),
      engine: 'rrweb',
    };
  }

  private onCdpEvent = (method: string, params: unknown, sessionId?: string): void => {
    if (!this.directory) return;
    if (method === 'Runtime.bindingCalled') {
      const body = params && typeof params === 'object' ? params as JsonObject : {};
      if (body.name !== BINDING || typeof body.payload !== 'string' || !sessionId) return;
      const event = this.assembler.push(body.payload);
      if (!event) return;
      const directory = this.directory;
      this.queue = this.queue.then(() => this.append(directory, sessionId, event)).catch(() => {});
      return;
    }
    if (method === 'Target.attachedToTarget') {
      const body = params && typeof params === 'object' ? params as JsonObject : {};
      const info = body.targetInfo && typeof body.targetInfo === 'object' ? body.targetInfo as PageTargetInfo : {};
      const sid = typeof body.sessionId === 'string' ? body.sessionId : undefined;
      if (!sid || info.type !== 'page' || skipUrl(info.url)) return;
      this.enqueueInstrument(sid);
      return;
    }
    if (method === 'Target.detachedFromTarget') {
      const body = params && typeof params === 'object' ? params as JsonObject : {};
      const sid = typeof body.sessionId === 'string' ? body.sessionId : sessionId;
      if (sid) this.instrumented.delete(sid);
    }
  };

  private enqueueInstrument(sessionId: string): void {
    this.instrumentQueue = this.instrumentQueue.then(() => this.instrument(sessionId), () => this.instrument(sessionId));
  }

  private async attachExisting(): Promise<void> {
    let infos: PageTargetInfo[] = [];
    try {
      const result = await this.session._call('Target.getTargets', {}) as { targetInfos?: PageTargetInfo[] };
      infos = Array.isArray(result.targetInfos) ? result.targetInfos : [];
    } catch { return; }
    for (const info of infos) {
      if (info.type !== 'page' || !info.targetId || skipUrl(info.url)) continue;
      try {
        const attached = await this.session._call('Target.attachToTarget', {
          targetId: info.targetId,
          flatten: true,
        }) as { sessionId?: string };
        if (typeof attached.sessionId === 'string') await this.instrument(attached.sessionId);
      } catch { /* Target may have closed. */ }
    }
  }

  private async instrument(sessionId: string): Promise<void> {
    if (!this.directory || this.instrumented.has(sessionId)) return;
    this.instrumented.add(sessionId);
    const script = await pageScript();
    try {
      await this.session._call('Runtime.enable', {}, { sessionId });
      await this.session._call('Page.enable', {}, { sessionId });
      try {
        await this.session._call('Runtime.addBinding', { name: BINDING }, { sessionId });
      } catch { /* Binding may already exist on a reused target. */ }
      await this.session._call('Page.addScriptToEvaluateOnNewDocument', { source: script }, { sessionId });
      await this.session._call('Runtime.evaluate', { expression: script }, { sessionId });
    } catch {
      this.instrumented.delete(sessionId);
    }
  }

  private async append(directory: string, sessionId: string, event: JsonObject): Promise<void> {
    const row: StoredEvent = { sid: sessionId, e: event };
    await appendFile(eventsPath(directory), JSON.stringify(row) + '\n', { mode: 0o600 });
  }

  private async flush(): Promise<void> {
    await this.instrumentQueue.catch(() => {});
    await this.queue.catch(() => {});
  }
}

async function resolveRecordingArg(arg?: string): Promise<string> {
  if (arg) {
    const candidate = resolve(arg);
    if (!(await stat(candidate)).isDirectory()) throw new Error(`not a recording directory: ${arg}`);
    return candidate;
  }
  const latest = await latestRecording();
  if (!latest) throw new Error('no recordings found');
  return latest;
}

async function serveReplay(directory: string): Promise<void> {
  const html = await readFile(REPLAY_URL);
  const vendor = await loadRrwebSource();
  const grouped = await loadRrwebEvents(directory);
  const sessions = [...grouped.entries()]
    .map(([sid, events]) => ({ sid, count: events.length }))
    .sort((a, b) => b.count - a.count);

  const server = createServer((req, res) => {
    const url = new URL(req.url || '/', 'http://127.0.0.1');
    if (url.pathname === '/' || url.pathname === '/index.html') {
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
      res.end(html);
      return;
    }
    if (url.pathname === '/rrweb.min.js' || url.pathname === '/vendor/rrweb.min.js') {
      res.writeHead(200, { 'content-type': 'text/javascript; charset=utf-8' });
      res.end(vendor);
      return;
    }
    if (url.pathname === '/sessions.json') {
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify(sessions));
      return;
    }
    if (url.pathname === '/events.json') {
      const sid = url.searchParams.get('sid') || sessions[0]?.sid || '';
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify(grouped.get(sid) ?? []));
      return;
    }
    res.writeHead(404);
    res.end('not found');
  });

  await new Promise<void>((resolveListen, reject) => {
    server.listen(0, '127.0.0.1', () => resolveListen());
    server.on('error', reject);
  });
  const address = server.address();
  const port = address && typeof address === 'object' ? address.port : 0;
  console.log(`replay: http://127.0.0.1:${port}/`);
  console.log(`recording: ${directory}`);
  console.log('Ctrl+C to stop');
  await new Promise<void>(resolveStop => {
    const stop = () => {
      server.close(() => resolveStop());
    };
    process.once('SIGINT', stop);
    process.once('SIGTERM', stop);
  });
}

async function runRecordingsCli(args: string[]): Promise<number> {
  if (args.length === 1 && args[0] === '--latest') {
    const latest = await latestRecording();
    if (!latest) {
      console.error('no recordings found');
      return 1;
    }
    console.log(latest);
    return 0;
  }
  if (args.length === 1 && (args[0] === 'enable' || args[0] === 'disable')) {
    const enabled = args[0] === 'enable';
    await setAutoRecording(enabled);
    console.log(`auto-recording preference ${enabled ? 'enabled' : 'disabled'}`);
    return 0;
  }
  if (args[0] === 'replay') {
    const directory = await resolveRecordingArg(args[1]);
    await serveReplay(directory);
    return 0;
  }
  if (args.length) {
    console.error('usage: browser-harness-js recordings [--latest|enable|disable|replay [dir]]');
    return 2;
  }
  const setting = await autoRecordingSetting();
  const active = await activeRecording();
  const latest = await latestRecording();
  console.log(`auto-recording: ${setting.enabled ? 'on' : 'off'} (${setting.source})`);
  console.log('engine: rrweb');
  console.log(`active: ${active || 'none'}`);
  console.log(`latest: ${latest || 'none'}`);
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  runRecordingsCli(process.argv.slice(2)).then(code => { process.exitCode = code; }).catch(error => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
