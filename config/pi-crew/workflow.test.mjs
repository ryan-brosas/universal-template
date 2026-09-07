import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { registerCrew } from './crew.mjs';

async function fixture(t, options = {}) {
  const root = await mkdtemp(join(tmpdir(), 'crew-flow-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  await writeFile(join(root, 'evidence.md'), 'The queue acknowledges receipt, not retention.\n');
  const rows = [], calls = [], messages = [], hooks = {}, commands = {};
  const ctx = { cwd: root, isProjectTrusted: () => true, sessionManager: { getSessionId: () => 'session-A' }, ui: { notify() {} } };
  const reply = args => ({ id: 'reply-' + args.id, actorId: args.id, direction: 'out', action: 'message', text: 'Queue receipt is not retention.', data: { requestId: args.data.requestId, proposal: { content: 'Verify retention separately from queue receipt.', evidence: { path: 'evidence.md', quote: 'The queue acknowledges receipt, not retention.' } } } });
  const call = async (ref, args) => {
    calls.push([ref, args]);
    if (ref === 'agents.self') return { kind: 'root', rootId: 'main', ownerHostId: 'main' };
    if (ref === 'agents.actors') return rows;
    if (ref === 'agents.create') { const row = { ...args, id: 'actor-' + rows.length, status: 'idle', rootId: 'main' }; rows.push(row); return row; }
    if (ref === 'agents.tell') return { queued: true };
    if (ref === 'agents.ask') return options.ask ? options.ask(args, reply) : reply(args);
    if (ref === 'extensions.hindsight_recall') return { text: '{"results":[]}' };
    if (ref === 'extensions.hindsight_retain') return options.retain ? options.retain(args) : { text: '{"documentId":"receipt"}' };
    throw Error('unexpected ' + ref);
  };
  const pi = { events: { emit() {}, on() {} }, on: (n, h) => hooks[n] = h, registerCommand: (n, c) => commands[n] = c, sendMessage: (m, o) => options.deliver ? options.deliver(m, o) : messages.push([m, o]) };
  const crew = registerCrew(pi, { configDir: '.pi', sharedRoot: root, env: {} });
  const context = { invocation: { extensionContext: ctx }, signal: new AbortController().signal, call, guide() {} };
  await crew.component.activate(context);
  return { ...crew, context, root, rows, calls, messages, hooks, commands, ctx };
}

const retains = f => f.calls.filter(([r]) => r === 'extensions.hindsight_retain');
const asks = f => f.calls.filter(([r]) => r === 'agents.ask');

test('automatic input reaches Main and project-pinned candidate retention without blocking input', async t => {
  const f = await fixture(t);
  assert.equal(typeof f.hooks.input, 'function', 'input stage must be registered');
  assert.deepEqual(f.hooks.input({ text: 'Review the queue', source: 'interactive' }, f.ctx), { action: 'continue' });
  await f.drain();
  assert.equal(asks(f).length, 2);
  assert.equal(retains(f).length, 2);
  assert.equal(f.messages.length, 2);
  for (const [, args] of retains(f)) {
    assert.match(args.bank, /^pi-crew-[0-9a-f]{24}$/);
    assert.ok(args.tags.includes('crew-session:session-A'));
    assert.ok(args.tags.includes('crew-kind:source-checked-proposal'));
    assert.match(args.content, /UNVERIFIED PROPOSAL/);
    assert.ok(args.documentId);
  }
  for (const [message, options] of f.messages) {
    assert.equal(options.triggerTurn, false);
    assert.equal(options.deliverAs, 'nextTurn');
    assert.match(message.content, /Queue receipt/);
  }
  f.hooks.input({ text: 'recursive message', source: 'extension' }, f.ctx);
  await f.drain();
  assert.equal(asks(f).length, 2);
});

test('component activation reuses all auto actors across sessions', async t => {
  const f = await fixture(t);
  const ids = f.rows.map(r => r.id);
  await f.component.activate(f.context);
  assert.deepEqual(f.rows.map(r => r.id), ids);
  assert.ok(f.status().auto.actors.every(a => a.reused));
});

test('compact dedupe is reserved before awaits; each role has at most one pending request', async t => {
  let release;
  const gate = new Promise(resolve => release = resolve);
  const f = await fixture(t, { ask: async (args, reply) => { await gate; return reply(args); } });
  const event = { compactionEntry: { id: 'cp' } };
  await Promise.all([f.hooks.session_compact(event, f.ctx), f.hooks.session_compact(event, f.ctx)]);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(asks(f).length, 2);
  release();
  await f.drain();
  await f.hooks.session_compact(event, f.ctx);
  await f.drain();
  assert.equal(retains(f).length, 2);
});

test('checkpoint dedupe survives more than 256 dispatches and resets on shutdown', async t => {
  const f = await fixture(t, { ask: async () => ({ action: 'silent' }) });
  for (let i = 0; i < 260; i++) {
    await f.hooks.session_compact({ compactionEntry: { id: 'cp-' + i } }, f.ctx);
    await f.drain();
  }
  const tells = () => f.calls.filter(([r]) => r === 'agents.tell').length;
  const before = [tells(), asks(f).length];
  await f.hooks.session_compact({ compactionEntry: { id: 'cp-0' } }, f.ctx);
  await f.drain();
  assert.deepEqual([tells(), asks(f).length], before);
  f.hooks.session_shutdown();
  await f.component.activate(f.context);
  await f.hooks.session_compact({ compactionEntry: { id: 'cp-0' } }, f.ctx);
  await f.drain();
  assert.deepEqual([tells(), asks(f).length], [before[0] + 1, before[1] + 2]);
});

test('bad provenance, mismatched responses and silent responses never retain', async t => {
  for (const alter of [
    r => ({ ...r, actorId: 'foreign' }),
    r => ({ ...r, data: { ...r.data, requestId: 'wrong' } }),
    r => ({ ...r, action: 'silent' }),
    r => ({ ...r, stale: true }),
    r => ({ ...r, error: 'failed' }),
    r => ({ ...r, data: { ...r.data, proposal: { content: 'unsupported', evidence: { path: '../outside.md', quote: 'x' } } } }),
    r => ({ ...r, data: { ...r.data, proposal: { content: 'unsupported', evidence: { path: 'evidence.md', quote: 'not present' } } } }),
  ]) {
    const f = await fixture(t, { ask: async (args, reply) => alter(reply(args)) });
    f.hooks.agent_settled({}, f.ctx);
    await f.drain();
    assert.equal(retains(f).length, 0);
  }
});

test('retention errors stay visible and shutdown discards late replies', async t => {
  const failed = await fixture(t, { retain: async () => ({ isError: true, text: 'offline' }) });
  failed.hooks.agent_settled({}, failed.ctx);
  await failed.drain();
  assert.equal(failed.messages.length, 2, 'findings still reach Main');
  assert.match(JSON.stringify(failed.status()), /retain unavailable/);
  let release;
  const gate = new Promise(resolve => release = resolve);
  const late = await fixture(t, { ask: async (args, reply) => { await gate; return reply(args); } });
  late.hooks.agent_settled({}, late.ctx);
  await new Promise(resolve => setImmediate(resolve));
  late.hooks.session_shutdown();
  release();
  await late.drain();
  assert.equal(retains(late).length, 0);
  assert.equal(late.messages.length, 0);
});

test('async delivery rejection is reported, and missing checkpoints do not dispatch', async t => {
  const f = await fixture(t, { deliver: async () => { throw Error('delivery unavailable'); } });
  await f.hooks.session_compact({}, f.ctx);
  await f.drain();
  assert.equal(asks(f).length, 0);
  assert.match(f.status().reflectionError, /checkpoint/);
  f.hooks.agent_settled({}, f.ctx);
  await f.drain();
  assert.equal(retains(f).length, 0);
  assert.match(JSON.stringify(f.status()), /delivery unavailable/);
});

test('project banks stay distinct and evidence symlinks cannot escape the root', async t => {
  const first = await fixture(t);
  const second = await fixture(t);
  first.hooks.agent_settled({}, first.ctx);
  second.hooks.agent_settled({}, second.ctx);
  await Promise.all([first.drain(), second.drain()]);
  assert.notEqual(retains(first)[0][1].bank, retains(second)[0][1].bank);
  const escaped = await fixture(t, { ask: async (args, reply) => {
    const r = reply(args); r.data.proposal.evidence.path = 'escape.md'; return r;
  } });
  await symlink(join(first.root, 'evidence.md'), join(escaped.root, 'escape.md'));
  escaped.hooks.agent_settled({}, escaped.ctx);
  await escaped.drain();
  assert.equal(retains(escaped).length, 0);
  assert.match(JSON.stringify(escaped.status()), /outside project/);
});

test('Hindsight outbox receipt is reported as queued, never completed retention', async t => {
  const f = await fixture(t, { retain: async () => ({ details: { documentId: 'queued-doc', enqueued: true, sent: 0 } }) });
  f.hooks.agent_settled({}, f.ctx);
  await f.drain();
  assert.ok(Object.values(f.status().auto.results).every(r => r.state === 'retention-queued'));
});
