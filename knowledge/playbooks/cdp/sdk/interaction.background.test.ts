import assert from 'node:assert/strict';
import { createServer, type Server } from 'node:http';
import test, { after, before } from 'node:test';
import { InteractionController } from './interaction.ts';
import { Session } from './session.ts';
import { closeTestBrowser, launchTestBrowser, type TestBrowser } from './test-browser-fixture.ts';

// Local regression: trusted guarded input must work in a background target and
// must not request Chrome-side activation.
//
// This covers the parallel/unattended promise the playbook documents: several
// agents drive their own tabs through explicit sessionId routing, while the
// human's window stays untouched. A separate browser profile is NOT what makes
// that true -- not calling `Target.activateTarget` / `Page.bringToFront` is.
//
// Local adaptation kept on upstream re-sync. It launches a disposable headless
// Chromium on its own profile and an ephemeral debug port, so it never attaches
// to the user's browser and never touches the shared REPL daemon (port 9876).

const PAGE = `<!doctype html>
<html><head><title>Background input</title></head>
<body>
  <button id="save" aria-label="Save draft">save</button>
  <input id="note" aria-label="Note">
  <output id="log"></output>
<script>
  const log = text => { document.getElementById('log').textContent += text + ';'; };
  document.getElementById('save').addEventListener('click', () => log('saved'));
  document.getElementById('note').addEventListener('input', () => log('typed'));
<\/script>
</body></html>`;

let chrome: TestBrowser | undefined;
let server: Server | undefined;
let port = 0;
let origin = '';

before(async () => {
  server = createServer((_req, res) => {
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
    res.end(PAGE);
  });
  await new Promise<void>(resolve => server!.listen(0, '127.0.0.1', resolve));
  origin = `http://127.0.0.1:${(server.address() as { port: number }).port}`;
  chrome = await launchTestBrowser({ profilePrefix: 'browser-harness-js-background-' });
  if (!chrome) return;
  port = chrome.port;
});

after(async () => {
  try { await closeTestBrowser(chrome); }
  finally {
    server?.closeAllConnections();
    await new Promise<void>(resolve => server ? server.close(() => resolve()) : resolve());
  }
});

test('trusted input reaches a background target without requesting activation', async t => {
  if (!chrome) return t.skip('Chrome not found (set CHROME_PATH)');
  const session = new Session();
  let targetId: string | undefined;
  const methods: string[] = [];
  try {
    await session.connect({ port });
    const original = session._call.bind(session);
    (session as any)._call = (method: string, params?: unknown, opts?: unknown, reconnected?: boolean) => {
      methods.push(method);
      return (original as any)(method, params, opts, reconnected);
    };

    const created = await session.domains.Target.createTarget({ url: 'about:blank', background: true }) as { targetId: string };
    targetId = created.targetId;
    const attached = await session.domains.Target.attachToTarget({ targetId, flatten: true }) as { sessionId: string };
    const scope = { sessionId: attached.sessionId };
    await original('Page.enable', {}, { sessionId: scope.sessionId });
    // Subscribe before navigation; readyState could describe the initial blank page.
    await Promise.all([
      session.waitFor({ method: 'Page.loadEventFired', sessionId: scope.sessionId, timeoutMs: 5_000 }),
      original('Page.navigate', { url: `${origin}/` }, { sessionId: scope.sessionId }),
    ]);

    const guard = new InteractionController(session, { allowedOrigins: [origin], input: 'trusted' });
    const startedAt = methods.length;

    let seen = await guard.observe({ scope });
    const save = seen.candidates.find(c => c.label === 'Save draft');
    assert.ok(save, `no Save draft candidate: ${seen.candidates.map(c => c.label).join(', ')}`);
    assert.ok(save.operations.includes('click'), `click not offered: ${save.operations.join(', ')}`);
    assert.equal((await guard.act({ scope, observationId: seen.observationId, action: { targetId: save.id, operation: 'click' } })).status, 'executed');

    seen = await guard.observe({ scope });
    const note = seen.candidates.find(c => c.label === 'Note');
    assert.ok(note, `no Note candidate: ${seen.candidates.map(c => c.label).join(', ')}`);
    assert.equal((await guard.act({ scope, observationId: seen.observationId, action: { targetId: note.id, operation: 'type', text: 'background text' } })).status, 'executed');
    const read = await session._call('Runtime.evaluate', {
      expression: 'JSON.stringify({ log: document.getElementById("log").textContent, note: document.getElementById("note").value })',
      returnByValue: true,
    }, { sessionId: scope.sessionId }) as { result: { value: string } };
    const state = JSON.parse(read.result.value) as { log: string; note: string };
    assert.equal(state.log, 'saved;typed;');
    assert.equal(state.note, 'background text');

    const during = methods.slice(startedAt);
    assert.ok(during.includes('Emulation.setFocusEmulationEnabled'), `expected focus emulation; saw ${[...new Set(during)].join(', ')}`);
    const activation = during.filter(method => method === 'Target.activateTarget' || method === 'Page.bringToFront');
    assert.deepEqual(activation, [], `guarded input must not request Chrome-side activation; saw ${activation.join(', ')}`);
    guard.close();
  } finally {
    if (targetId) await session.domains.Target.closeTarget({ targetId }).catch(() => {});
    if (session.isConnected()) session.close();
  }
});
