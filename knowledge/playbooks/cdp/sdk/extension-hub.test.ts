import assert from 'node:assert/strict';
import test from 'node:test';
import {
  extensionConnected,
  getExtensionClient,
  resetExtensionHub,
  setExtensionClient,
  waitForExtension,
} from './extension-hub.ts';
import { WIRE_CLOSED, WIRE_OPEN, type Wire, type WireEventType, type WireListener } from './wire.ts';

class FakeWire implements Wire {
  readyState = WIRE_OPEN;
  private listeners: Record<WireEventType, WireListener[]> = {
    message: [], close: [], error: [], open: [],
  };
  send(_data: string) {}
  close() {
    this.readyState = WIRE_CLOSED;
    for (const fn of this.listeners.close) fn({});
  }
  addEventListener(type: WireEventType, listener: WireListener) {
    this.listeners[type].push(listener);
  }
}

test.afterEach(() => resetExtensionHub());

test('waitForExtension resolves immediately when a client is already up', async () => {
  const wire = new FakeWire();
  setExtensionClient(wire);
  assert.equal(extensionConnected(), true);
  assert.equal(await waitForExtension(10), wire);
  assert.equal(getExtensionClient(), wire);
});

test('waitForExtension resolves when the client connects later', async () => {
  const pending = waitForExtension(200);
  const wire = new FakeWire();
  setExtensionClient(wire);
  assert.equal(await pending, wire);
});

test('waitForExtension times out when nothing connects', async () => {
  await assert.rejects(waitForExtension(20), /timed out after 20ms/);
});

test('a closed client is no longer offered', () => {
  const wire = new FakeWire();
  setExtensionClient(wire);
  wire.close();
  assert.equal(getExtensionClient(), undefined);
  assert.equal(extensionConnected(), false);
});
