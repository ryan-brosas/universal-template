import assert from 'node:assert/strict';
import test from 'node:test';
import { getBrowserCandidates, Session } from './session.ts';
import { resetExtensionHub, setExtensionClient } from './extension-hub.ts';
import { WIRE_CLOSED, WIRE_OPEN, type Wire, type WireEventType, type WireListener } from './wire.ts';

class FakeWire implements Wire {
  readyState = WIRE_OPEN;
  sent: string[] = [];
  private listeners: Record<WireEventType, WireListener[]> = {
    message: [], close: [], error: [], open: [],
  };
  send(data: string) {
    this.sent.push(data);
    const msg = JSON.parse(data) as { id: number; method: string };
    const result = msg.method === 'Target.getTargets' ? { targetInfos: [] } : {};
    queueMicrotask(() => this.emit('message', { data: JSON.stringify({ id: msg.id, result }) }));
  }
  close() {
    this.readyState = WIRE_CLOSED;
    this.emit('close', {});
  }
  addEventListener(type: WireEventType, listener: WireListener) {
    this.listeners[type].push(listener);
  }
  emit(type: WireEventType, ev: { data?: string }) {
    for (const fn of this.listeners[type]) fn(ev);
  }
}

test('getBrowserCandidates includes Helium on every supported platform', () => {
  assert.deepEqual(
    getBrowserCandidates('/Users/me', 'darwin').find(candidate => candidate.name === 'Helium'),
    {
      name: 'Helium',
      profileDir: '/Users/me/Library/Application Support/net.imput.helium',
    },
  );
  assert.deepEqual(
    getBrowserCandidates('/home/me', 'linux').find(candidate => candidate.name === 'Helium'),
    {
      name: 'Helium',
      profileDir: '/home/me/.config/net.imput.helium',
    },
  );
  assert.deepEqual(
    getBrowserCandidates('C:\\Users\\me', 'win32', 'C:\\Users\\me\\AppData\\Local').find(
      candidate => candidate.name === 'Helium',
    ),
    {
      name: 'Helium',
      profileDir: 'C:\\Users\\me\\AppData\\Local\\imput\\Helium\\User Data',
    },
  );
});

test('connect auto prefers a live extension wire over remote debugging', async () => {
  resetExtensionHub();
  const wire = new FakeWire();
  setExtensionClient(wire);
  const session = new Session();
  await session.connect({ extensionWaitMs: 20 });
  assert.equal(session.isConnected(), true);
  assert.equal(session.getTransport(), 'extension');
  const { targetInfos } = await session.domains.Target.getTargets({});
  assert.deepEqual(targetInfos, []);
  session.setActiveSession('sid-keep');
  await session._call('Chrome.group', { tabIds: ['1'] });
  const chromeMsg = JSON.parse(wire.sent.at(-1)!) as { method: string; sessionId?: string };
  assert.equal(chromeMsg.method, 'Chrome.group');
  assert.equal(chromeMsg.sessionId, undefined);
  session.close();
  resetExtensionHub();
});

test('connect({ transport: "extension" }) fails closed when the extension is absent', async () => {
  resetExtensionHub();
  const session = new Session();
  await assert.rejects(
    session.connect({ transport: 'extension', timeoutMs: 30 }),
    /timed out after 30ms waiting for the browser-harness-js extension/,
  );
});
