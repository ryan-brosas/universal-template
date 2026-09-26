import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { PassThrough } from 'node:stream';
import test from 'node:test';
import { closeTestBrowser, launchTestBrowser, selectTestBrowserExecutable, type TestBrowserProcess } from './test-browser-fixture.ts';

class FakeBrowserProcess extends EventEmitter implements TestBrowserProcess {
  exitCode: number | null = null;
  signalCode: NodeJS.Signals | null = null;
  stderr = new PassThrough();
  killedWith: Array<NodeJS.Signals | number | undefined> = [];
  exitOnKill = true;

  kill(signal?: NodeJS.Signals | number): boolean {
    this.killedWith.push(signal);
    if (this.exitOnKill) {
      queueMicrotask(() => {
        this.exitCode = null;
        this.signalCode = typeof signal === 'string' ? signal : 'SIGTERM';
        this.emit('exit', this.exitCode, this.signalCode);
      });
    }
    return true;
  }
}

const depsFor = (overrides: {
  exists?: (path: string) => boolean;
  readFile?: (path: string) => string;
  tcpConnect?: (port: number) => Promise<void>;
  spawn?: () => FakeBrowserProcess;
  sleep?: (ms: number) => Promise<void>;
  removed?: string[];
} = {}) => ({
  existsSync: (path: any) => overrides.exists?.(String(path)) ?? false,
  mkdtempSync: () => '/owned/profile',
  readFileSync: (path: any) => overrides.readFile?.(String(path)) ?? '',
  rmSync: (path: any) => { overrides.removed?.push(String(path)); },
  spawn: () => overrides.spawn?.() ?? new FakeBrowserProcess(),
  tcpConnect: overrides.tcpConnect ?? (async () => {}),
  sleep: overrides.sleep ?? (async () => {}),
});

test('explicit CHROME_PATH never falls back to another browser', () => {
  assert.throws(
    () => selectTestBrowserExecutable({ env: { CHROME_PATH: '/missing/chrome' }, candidates: ['/usr/bin/chromium'], existsSync: path => String(path) === '/usr/bin/chromium' }),
    /CHROME_PATH is set but does not exist: \/missing\/chrome/,
  );
});

test('no executable is the only skip path', async () => {
  const browser = await launchTestBrowser({
    profilePrefix: 'browser-harness-js-test-',
    env: {},
    candidates: ['/missing/chrome'],
    startupTimeoutMs: 1,
    deps: depsFor(),
  });
  assert.equal(browser, undefined);
});

test('spawn failure fails startup with selected browser diagnostics', async () => {
  const child = new FakeBrowserProcess();
  const removed: string[] = [];
  await assert.rejects(
    launchTestBrowser({
      profilePrefix: 'browser-harness-js-test-',
      env: {},
      candidates: ['/bin/chrome'],
      startupTimeoutMs: 100,
      deps: depsFor({
        removed,
        exists: path => path === '/bin/chrome',
        spawn: () => {
          queueMicrotask(() => child.emit('error', new Error('spawn EACCES')));
          return child;
        },
        sleep: async () => { await Promise.resolve(); },
      }),
    }),
    /Browser startup failed to start.*\/bin\/chrome.*stderr tail: <empty>/,
  );
  assert.deepEqual(removed, ['/owned/profile']);
});

test('early browser exit fails promptly with captured stderr', async () => {
  const child = new FakeBrowserProcess();
  child.exitOnKill = false;
  await assert.rejects(
    launchTestBrowser({
      profilePrefix: 'browser-harness-js-test-',
      env: {},
      candidates: ['/bin/chrome'],
      startupTimeoutMs: 1000,
      deps: depsFor({
        exists: path => path === '/bin/chrome',
        spawn: () => {
          queueMicrotask(() => {
            child.stderr.write('zygote failed\n');
            child.exitCode = 13;
            child.emit('exit', 13, null);
          });
          return child;
        },
        sleep: async () => { await Promise.resolve(); },
      }),
    }),
    /exited before DevToolsActivePort became ready \(code=13, signal=null\).*zygote failed/,
  );
});

test('invalid or missing DevToolsActivePort port never reaches tests as port 0', async () => {
  const child = new FakeBrowserProcess();
  await assert.rejects(
    launchTestBrowser({
      profilePrefix: 'browser-harness-js-test-',
      env: {},
      candidates: ['/bin/chrome'],
      startupTimeoutMs: 1,
      pollIntervalMs: 1,
      deps: depsFor({
        exists: path => path === '/bin/chrome' || path.endsWith('/DevToolsActivePort'),
        readFile: () => '\n/devtools/browser/fake',
        spawn: () => child,
      }),
    }),
    /positive DevToolsActivePort TCP port.*invalid DevToolsActivePort port line: ""/,
  );
  assert.deepEqual(child.killedWith, ['SIGTERM']);
});

test('startup waits for a real TCP listener on the positive port', async () => {
  await assert.rejects(
    launchTestBrowser({
      profilePrefix: 'browser-harness-js-test-',
      env: {},
      candidates: ['/bin/chrome'],
      startupTimeoutMs: 1,
      pollIntervalMs: 1,
      deps: depsFor({
        exists: path => path === '/bin/chrome' || path.endsWith('/DevToolsActivePort'),
        readFile: () => '9222\n/devtools/browser/fake',
        tcpConnect: async port => { throw new Error('connection refused ' + port); },
      }),
    }),
    /positive DevToolsActivePort TCP port.*connection refused 9222/,
  );
});

test('successful startup returns only the owned validated port and cleanup releases listeners', async () => {
  const child = new FakeBrowserProcess(); const removed: string[] = []; const connected: number[] = [];
  const browser = await launchTestBrowser({
    profilePrefix: 'browser-harness-js-test-', env: {}, candidates: ['/bin/chrome'],
    deps: depsFor({
      exists: path => path === '/bin/chrome' || path.endsWith('/DevToolsActivePort'),
      readFile: () => '32123\n/devtools/browser/fake', spawn: () => child,
      tcpConnect: async port => { connected.push(port); },
    }),
  });
  assert.equal(browser?.port, 32123); assert.deepEqual(connected, [32123]);
  await closeTestBrowser(browser, { deps: { rmSync: path => { removed.push(String(path)); } } });
  assert.deepEqual(removed, ['/owned/profile']); assert.equal(child.listenerCount('exit'), 0);
});

test('unconfirmed termination fails closed and preserves the owned profile', async () => {
  const child = new FakeBrowserProcess(); child.exitOnKill = false; const removed: string[] = [];
  await assert.rejects(closeTestBrowser(
    { executablePath: '/bin/chrome', profileDir: '/owned/profile', port: 9222, process: child },
    { cleanupTimeoutMs: 1, deps: { rmSync: path => { removed.push(String(path)); } } },
  ), /did not exit after SIGKILL/);
  assert.deepEqual(child.killedWith, ['SIGTERM', 'SIGKILL']);
  assert.deepEqual(removed, []); assert.equal(child.listenerCount('exit'), 0);
});

test('cleanup does not wait forever for a process that already exited by signal', async () => {
  const child = new FakeBrowserProcess();
  child.signalCode = 'SIGTERM';
  child.exitOnKill = false;
  const removed: string[] = [];
  await closeTestBrowser(
    { executablePath: '/bin/chrome', profileDir: '/owned/profile', port: 9222, process: child },
    { cleanupTimeoutMs: 1, deps: { rmSync: (path: any) => { removed.push(String(path)); } } },
  );
  assert.deepEqual(child.killedWith, []);
  assert.deepEqual(removed, ['/owned/profile']);
});
