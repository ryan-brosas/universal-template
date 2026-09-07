import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { registerCrew, definitions } from './crew.mjs';

async function fixture(t, mutate = x => x) {
 const root = await mkdtemp(join(tmpdir(), 'crew-lineage-'));
 t.after(() => rm(root, { recursive: true, force: true }));
 const rows = definitions(root, '/shared').map((d, i) => mutate({ ...d, id: String(i), rootId: 'main-B', status: 'idle' }));
 const hooks = {}, commands = {}, notices = [], guides = [], calls = [];
 const ctx = { cwd: root, isProjectTrusted: () => true, sessionManager: { getSessionId: () => 'B' }, ui: { notify: (...args) => notices.push(args) } };
 const pi = { events: { emit() {}, on() {} }, on: (n, h) => hooks[n] = h, registerCommand: (n, c) => commands[n] = c };
 const crew = registerCrew(pi, { configDir: '.pi', sharedRoot: '/shared', env: {} });
 await crew.component.activate({ invocation: { extensionContext: ctx }, signal: new AbortController().signal, guide: g => guides.push(g), call: async (ref, args) => {
  calls.push([ref, args]);
  if (ref === 'agents.self') return { kind: 'root', rootId: 'main-B' };
  if (ref === 'agents.actors') return rows;
  if (ref === 'agents.tell') return {};
  throw Error('Unexpected mutation: ' + ref);
 } });
 return { ...crew, hooks, commands, notices, guides, calls, ctx, rows };
}

test('foreign observer lineage is degraded, visible, and preserved', async t => {
 const f = await fixture(t, a => ({ ...a, rootId: 'main-A' }));
 assert.equal(f.status().state, 'degraded');
 assert.equal(f.status().observerCoverage.rootId, 'main-B');
 assert.deepEqual(f.status().observerCoverage.gaps.map(g => g.name), ['project-supervisor', 'project-advisor']);
 assert.ok(f.notices.some(n => /degraded/i.test(n[0])));
 assert.ok(f.guides.some(g => /degraded/i.test(g.content)));
 assert.ok(f.rows.every(a => a.rootId === 'main-A'));
 await f.commands.crew.handler('', f.ctx);
 assert.match(f.notices.at(-1)[0], /degraded/);
});

test('same-root subscriptions are configured; missing root or events fail closed', async t => {
 const good = await fixture(t);
 assert.equal(good.status().state, 'active');
 for (const change of [a => ({ ...a, rootId: undefined }), a => ({ ...a, events: [] })]) {
  const bad = await fixture(t, change);
  assert.equal(bad.status().state, 'degraded');
  assert.equal(bad.status().observerCoverage.gaps.length, 2);
 }
});

test('foreign legacy reflector receives explicit checkpoint instead of silent deferral', async t => {
 const f = await fixture(t, a => a.name === 'session-reflector' ? { ...a, rootId: 'main-A', events: ['session_compact'] } : a);
 await f.hooks.session_compact({ compactionEntry: { id: 'checkpoint-B' } }, f.ctx);
 const tells = f.calls.filter(([ref]) => ref === 'agents.tell');
 assert.equal(tells.length, 1);
 assert.equal(tells[0][1].data.sessionId, 'B');
 assert.equal(tells[0][1].data.checkpointId, 'checkpoint-B');
});
