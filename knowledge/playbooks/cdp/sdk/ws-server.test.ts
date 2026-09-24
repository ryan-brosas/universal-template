import assert from 'node:assert/strict';
import test from 'node:test';
import { createServer } from 'node:http';
import { acceptExtensionUpgrade, isExtensionUpgrade } from './ws-server.ts';

function listen(server: ReturnType<typeof createServer>): Promise<number> {
  return new Promise((resolve, reject) => {
    server.listen(0, '127.0.0.1', () => {
      const addr = server.address();
      if (typeof addr === 'object' && addr) resolve(addr.port);
      else reject(new Error('no port'));
    });
    server.on('error', reject);
  });
}

test('isExtensionUpgrade only accepts /extension websocket', () => {
  const req = {
    url: '/extension',
    headers: {
      upgrade: 'websocket',
      connection: 'Upgrade',
      'sec-websocket-key': 'x',
    },
  };
  assert.equal(isExtensionUpgrade(req as any), true);
  assert.equal(isExtensionUpgrade({ ...req, url: '/eval' } as any), false);
});

test('text frames round-trip over the /extension upgrade', async () => {
  const server = createServer((_req, res) => {
    res.writeHead(404);
    res.end();
  });
  server.on('upgrade', (req, socket, head) => {
    if (!isExtensionUpgrade(req)) {
      socket.destroy();
      return;
    }
    acceptExtensionUpgrade(req, socket, head, ws => {
      ws.onMessage(text => ws.send('echo:' + text));
    });
  });
  const port = await listen(server);
  try {
    const client = new WebSocket(`ws://127.0.0.1:${port}/extension`);
    const opened = new Promise<void>((resolve, reject) => {
      client.addEventListener('open', () => resolve());
      client.addEventListener('error', () => reject(new Error('client error')));
    });
    await opened;
    const got = new Promise<string>((resolve, reject) => {
      client.addEventListener('message', ev => resolve(String(ev.data)));
      client.addEventListener('error', () => reject(new Error('message error')));
    });
    client.send('hello');
    assert.equal(await got, 'echo:hello');
    client.close();
  } finally {
    server.close();
  }
});
