import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { connect as connectTcp } from 'node:net';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import type { ChildProcess } from 'node:child_process';
import type { PathLike } from 'node:fs';

const DEFAULT_STARTUP_TIMEOUT_MS = 30_000;
const DEFAULT_CLEANUP_TIMEOUT_MS = 5_000;
const DEFAULT_POLL_INTERVAL_MS = 100;
const STDERR_LIMIT = 8192;

export type TestBrowserProcess = Pick<ChildProcess, 'exitCode' | 'signalCode' | 'stderr' | 'kill' | 'once' | 'off'>;

export type TestBrowser = {
  executablePath: string;
  profileDir: string;
  port: number;
  process: TestBrowserProcess;
};

type SpawnOptions = { stdio: ['ignore', 'ignore', 'pipe'] };

type BrowserFixtureDeps = {
  existsSync: (path: PathLike) => boolean;
  mkdtempSync: (prefix: string) => string;
  readFileSync: (path: PathLike, encoding: BufferEncoding) => string;
  rmSync: (path: PathLike, options: { recursive: true; force: true; maxRetries: number; retryDelay: number }) => void;
  spawn: (file: string, args: string[], options: SpawnOptions) => TestBrowserProcess;
  tcpConnect: (port: number) => Promise<void>;
  sleep: (ms: number) => Promise<void>;
};

type LaunchTestBrowserOptions = {
  profilePrefix: string;
  env?: NodeJS.ProcessEnv;
  candidates?: string[];
  startupTimeoutMs?: number;
  pollIntervalMs?: number;
  deps?: Partial<BrowserFixtureDeps>;
};

type CloseTestBrowserOptions = {
  cleanupTimeoutMs?: number;
  deps?: Pick<BrowserFixtureDeps, 'rmSync'>;
};

const defaultCandidates = [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
];

const defaultDeps: BrowserFixtureDeps = {
  existsSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  spawn: (file, args, options) => spawn(file, args, options),
  tcpConnect: port => new Promise<void>((resolve, reject) => {
    const socket = connectTcp({ host: '127.0.0.1', port });
    const finish = (error?: Error) => {
      socket.setTimeout(0);
      socket.destroy();
      if (error) reject(error);
      else resolve();
    };
    socket.once('connect', () => finish());
    socket.once('error', finish);
    socket.setTimeout(1000, () => finish(new Error(`timed out connecting to 127.0.0.1:${port}`)));
  }),
  sleep: ms => new Promise(resolve => setTimeout(resolve, ms)),
};

function mergedDeps(overrides: Partial<BrowserFixtureDeps> | undefined): BrowserFixtureDeps {
  return { ...defaultDeps, ...overrides };
}

export function selectTestBrowserExecutable(options: {
  env?: NodeJS.ProcessEnv;
  candidates?: string[];
  existsSync?: (path: PathLike) => boolean;
} = {}): string | undefined {
  const env = options.env ?? process.env;
  const exists = options.existsSync ?? existsSync;
  const explicit = env.CHROME_PATH;
  if (explicit) {
    if (exists(explicit)) return explicit;
    throw new Error(`CHROME_PATH is set but does not exist: ${explicit}`);
  }
  return (options.candidates ?? defaultCandidates).find(candidate => exists(candidate));
}

export async function launchTestBrowser(options: LaunchTestBrowserOptions): Promise<TestBrowser | undefined> {
  const deps = mergedDeps(options.deps);
  const executablePath = selectTestBrowserExecutable({
    env: options.env,
    candidates: options.candidates,
    existsSync: deps.existsSync,
  });
  if (!executablePath) return undefined;

  const profileDir = deps.mkdtempSync(join(tmpdir(), options.profilePrefix));
  let browserProcess: TestBrowserProcess | undefined;
  try {
    const stderr = createBoundedText(STDERR_LIMIT);
    browserProcess = deps.spawn(executablePath, [
      '--headless=new',
      '--remote-debugging-port=0',
      `--user-data-dir=${profileDir}`,
      '--no-first-run',
      '--no-default-browser-check',
      '--window-size=1200,900',
      'about:blank',
    ], { stdio: ['ignore', 'ignore', 'pipe'] });
    browserProcess.stderr?.setEncoding?.('utf8');
    browserProcess.stderr?.on('data', chunk => stderr.append(String(chunk)));

    let spawnError: unknown;
    let exit: { code: number | null; signal: NodeJS.Signals | null } | undefined;
    browserProcess.once('error', error => { spawnError = error; });
    browserProcess.once('exit', (code, signal) => { exit = { code, signal }; });

    const portFile = join(profileDir, 'DevToolsActivePort');
    const deadline = Date.now() + (options.startupTimeoutMs ?? DEFAULT_STARTUP_TIMEOUT_MS);
    let lastReadinessError: unknown;
    do {
      if (spawnError) throw browserStartupError('failed to start', executablePath, profileDir, stderr.text(), spawnError);
      if (exit || hasExited(browserProcess)) {
        throw browserStartupError(
          `exited before DevToolsActivePort became ready (code=${exit?.code ?? browserProcess.exitCode}, signal=${exit?.signal ?? browserProcess.signalCode})`,
          executablePath,
          profileDir,
          stderr.text(),
        );
      }
      if (deps.existsSync(portFile)) {
        try {
          const port = parseDevToolsPort(deps.readFileSync(portFile, 'utf8'));
          await deps.tcpConnect(port);
          return { executablePath, profileDir, port, process: browserProcess };
        } catch (error) {
          lastReadinessError = error;
        }
      } else {
        lastReadinessError = new Error(`missing ${portFile}`);
      }
      await deps.sleep(options.pollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS);
    } while (Date.now() < deadline);
    throw browserStartupError(
      `timed out after ${options.startupTimeoutMs ?? DEFAULT_STARTUP_TIMEOUT_MS}ms waiting for a positive DevToolsActivePort TCP port; last readiness error: ${formatError(lastReadinessError)}`,
      executablePath,
      profileDir,
      stderr.text(),
    );
  } catch (error) {
    if (browserProcess) {
      try { await closeSpawnedBrowser(browserProcess, DEFAULT_CLEANUP_TIMEOUT_MS); }
      catch (cleanupError) {
        throw new AggregateError([error, cleanupError], `${formatError(error)}; cleanup failed; owned profile preserved`);
      }
    }
    deps.rmSync(profileDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
    throw error;
  }
}

export async function closeTestBrowser(browser: TestBrowser | undefined, options: CloseTestBrowserOptions = {}): Promise<void> {
  if (!browser) return;
  const deps = { rmSync, ...options.deps };
  await closeSpawnedBrowser(browser.process, options.cleanupTimeoutMs ?? DEFAULT_CLEANUP_TIMEOUT_MS);
  deps.rmSync(browser.profileDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}

function parseDevToolsPort(text: string): number {
  const [portLine = ''] = text.split('\n');
  const normalized = portLine.trim();
  const port = Number(normalized);
  if (!Number.isInteger(port) || port <= 0 || port > 65535) {
    throw new Error(`invalid DevToolsActivePort port line: ${JSON.stringify(portLine)}`);
  }
  return port;
}

function hasExited(process: TestBrowserProcess): boolean {
  return process.exitCode !== null || process.signalCode !== null;
}

async function closeSpawnedBrowser(process: TestBrowserProcess, timeoutMs: number): Promise<void> {
  if (hasExited(process)) return;
  const gracefulExit = waitForExit(process, timeoutMs);
  process.kill('SIGTERM');
  if (await gracefulExit || hasExited(process)) return;
  const forcedExit = waitForExit(process, Math.min(timeoutMs, 1000));
  process.kill('SIGKILL');
  if (!await forcedExit && !hasExited(process)) throw new Error('Owned test browser did not exit after SIGKILL');
}

function waitForExit(process: TestBrowserProcess, timeoutMs: number): Promise<boolean> {
  if (hasExited(process)) return Promise.resolve(true);
  return new Promise(resolve => {
    const finish = (exited: boolean) => {
      clearTimeout(timer);
      process.off('exit', onExit);
      resolve(exited);
    };
    const onExit = () => finish(true);
    const timer = setTimeout(() => finish(false), timeoutMs);
    process.once('exit', onExit);
  });
}

function browserStartupError(reason: string, executablePath: string, profileDir: string, stderr: string, cause?: unknown): Error {
  const stderrText = stderr ? `; stderr tail: ${stderr}` : '; stderr tail: <empty>';
  const error = new Error(`Browser startup ${reason} for ${executablePath} using owned profile ${profileDir}${stderrText}`);
  if (cause) (error as Error & { cause?: unknown }).cause = cause;
  return error;
}

function formatError(error: unknown): string {
  if (!error) return '<none>';
  if (error instanceof Error) return error.message;
  return String(error);
}

function createBoundedText(limit: number): { append(chunk: string): void; text(): string } {
  let text = '';
  let truncated = false;
  return {
    append(chunk: string) {
      text += chunk;
      if (text.length > limit) {
        text = text.slice(text.length - limit);
        truncated = true;
      }
    },
    text() {
      return truncated ? `<truncated>${text}` : text;
    },
  };
}
