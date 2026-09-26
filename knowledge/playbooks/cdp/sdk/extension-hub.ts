/**
 * Inbound extension connections. The MV3 service worker dials
 * `ws://127.0.0.1:<port>/extension`; the REPL upgrades that request and
 * registers the socket here. `Session.connect()` prefers this over
 * remote-debugging CDP.
 *
 * Last socket wins: one daemon, one browser at a time (same as today's
 * single `Session`). The previous socket is closed.
 */
import { WIRE_OPEN, type Wire, type WireListener } from './wire.ts';
import type { TextSocket } from './ws-server.ts';

type Waiter = {
  resolve: (wire: Wire) => void;
  reject: (err: Error) => void;
  timer: ReturnType<typeof setTimeout>;
};

let client: Wire | undefined;
let waiters: Waiter[] = [];

export function asWire(sock: TextSocket): Wire {
  const listeners: Record<'message' | 'close' | 'error' | 'open', WireListener[]> = {
    message: [],
    close: [],
    error: [],
    open: [],
  };
  sock.onMessage(text => {
    for (const fn of listeners.message) fn({ data: text });
  });
  sock.onClose(() => {
    for (const fn of listeners.close) fn({});
  });
  return {
    get readyState() {
      return sock.readyState;
    },
    send(data: string) {
      sock.send(data);
    },
    close() {
      sock.close();
    },
    addEventListener(type, listener) {
      listeners[type].push(listener);
    },
  };
}

export function setExtensionClient(wire: Wire): void {
  if (client && client !== wire) {
    try { client.close(); } catch { /* ignore */ }
  }
  client = wire;
  const ready = waiters.splice(0);
  for (const w of ready) {
    clearTimeout(w.timer);
    w.resolve(wire);
  }
  wire.addEventListener('close', () => {
    if (client === wire) client = undefined;
  });
}

export function getExtensionClient(): Wire | undefined {
  return client && client.readyState === WIRE_OPEN ? client : undefined;
}

export function extensionConnected(): boolean {
  return getExtensionClient() !== undefined;
}

export function waitForExtension(timeoutMs: number): Promise<Wire> {
  const existing = getExtensionClient();
  if (existing) return Promise.resolve(existing);
  return new Promise((resolve, reject) => {
    const waiter: Waiter = {
      resolve,
      reject,
      timer: setTimeout(() => {
        waiters = waiters.filter(w => w !== waiter);
        reject(new Error(
          `timed out after ${timeoutMs}ms waiting for the browser-harness-js extension`,
        ));
      }, timeoutMs),
    };
    waiters.push(waiter);
  });
}

/** Test-only: drop the current client and fail any waiters. */
export function resetExtensionHub(): void {
  const prev = client;
  client = undefined;
  const ready = waiters.splice(0);
  for (const w of ready) {
    clearTimeout(w.timer);
    w.reject(new Error('extension hub reset'));
  }
  if (prev) {
    try { prev.close(); } catch { /* ignore */ }
  }
}
