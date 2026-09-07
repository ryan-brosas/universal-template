import test from 'node:test';
import assert from 'node:assert/strict';
import { projectIdentity, digest } from './identity.mjs';
import { projectScoped, failure } from './memory.mjs';
import { AUTO_ROLES, STAGES, buildTriggers, shouldTrigger, scopeKey } from './trigger.mjs';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const inRepo = process.cwd();

test('project identity is stable, git-root canonical, and distinct per repo', async () => {
  const a = await projectIdentity(inRepo);
  const b = await projectIdentity(join(inRepo, 'roles'));
  assert.deepEqual({ ...a }, { ...b }, 'worktree-adjacent subdirs share one identity');
  assert.match(a.projectId, /^crew-[0-9a-f]{24}$/);
  assert.equal(a.bankId, 'pi-crew-' + a.id);
  const outside = await projectIdentity('/tmp');
  assert.notEqual(a.id, outside.id, 'unrelated directories must not share identity');
  assert.equal(digest('/x'), digest('/x'));
  await assert.rejects(projectIdentity('/definitely/not/here'), /Cannot resolve/);
});

test('memory broker scopes every call to the identity bank and role tag', async () => {
  const identity = await projectIdentity(inRepo);
  const calls = [];
  const extensions = {
    hindsight_recall: async args => { calls.push(['recall', args]); return { details: { results: [{ id: 'r1' }] } }; },
    hindsight_retain: async args => { calls.push(['retain', args]); return { details: { documentId: 'd1' } }; },
  };
  const memory = projectScoped(identity, extensions);
  const rows = await memory.recall('scout', 'context for task');
  assert.equal(rows.degraded, false); assert.equal(rows.rows[0].id, 'r1');
  const [kind, recallArgs] = calls[0];
  assert.equal(kind, 'recall');
  assert.equal(recallArgs.bank, identity.bankId, 'hard project bank pin');
  assert.deepEqual(recallArgs.tags, ['crew-role:scout']);
  assert.equal(recallArgs.tagsMatch, 'all_strict');
  const proposal = await memory.propose('verifier', { content: 'lesson', context: 'why', session: 's1', checkpoint: 'cp1', kind: 'failure-pattern' });
  assert.equal(proposal.degraded, false); assert.equal(proposal.documentId, 'd1');
  const [, retainArgs] = calls[1];
  assert.equal(retainArgs.bank, identity.bankId);
  assert.ok(retainArgs.tags.includes('crew-role:verifier'));
  assert.ok(retainArgs.tags.includes('crew-checkpoint:cp1'));
  assert.equal(retainArgs.metadata.crewProject, identity.projectId);
  const rejected = await memory.propose('verifier', { content: '   ', context: 'x', kind: 'x' });
  assert.equal(rejected.degraded, true); assert.match(rejected.reason, /empty proposal/);
});

test('memory broker degrades closed when Hindsight is missing or failing', async () => {
  const identity = await projectIdentity(inRepo);
  const none = projectScoped(identity, undefined);
  assert.equal(none.degraded, true);
  const broken = projectScoped(identity, { hindsight_recall: async () => { throw new Error('down'); } });
  const rows = await broken.recall('scout', 'q');
  assert.equal(rows.degraded, true); assert.match(rows.reason, /down/); assert.deepEqual(rows.rows, []);
  const failingRetain = projectScoped(identity, { hindsight_retain: async () => { throw new Error('offline'); } });
  const kept = await failingRetain.propose('scout', { content: 'c', context: 'x', kind: 'k' });
  assert.equal(kept.degraded, true); assert.match(kept.reason, /offline/);
});

test('captured Hindsight envelopes preserve recall rows and reject errors', async () => {
  const identity = await projectIdentity(inRepo);
  const envelopes = [
    { text: JSON.stringify({ results: [{ id: 'live-row' }] }), details: { bankId: identity.bankId }, isError: false },
    { content: [{ type: 'text', text: JSON.stringify({ results: [{ id: 'live-row' }] }) }] },
  ];
  for (const envelope of envelopes) {
    const broker = projectScoped(identity, { hindsight_recall: async () => envelope });
    assert.deepEqual((await broker.recall('scout', 'q')).rows, [{ id: 'live-row' }]);
  }
  for (const envelope of [{ isError: true, text: 'service unavailable' }, { text: 'not JSON' }, { results: 'invalid' }, {}]) {
    const broker = projectScoped(identity, { hindsight_recall: async () => envelope });
    assert.equal((await broker.recall('scout', 'q')).degraded, true);
  }
});

test('captured Hindsight retain requires a receipt, not just a resolved call', async () => {
  const identity = await projectIdentity(inRepo);
  const proposal = { content: 'lesson', context: 'evidence', kind: 'candidate' };
  for (const envelope of [{ isError: true, text: 'offline' }, {}, { text: '{"success":false}' }]) {
    const broker = projectScoped(identity, { hindsight_retain: async () => envelope });
    assert.equal((await broker.propose('scout', proposal)).degraded, true);
  }
  const broker = projectScoped(identity, { hindsight_retain: async () => ({ text: '{"documentId":"receipt-1"}', details: { bankId: identity.bankId } }) });
  assert.deepEqual(await broker.propose('scout', proposal), { degraded: false, documentId: 'receipt-1' });
});

test('automatic trigger set is stage-bounded and reuses existing durable actors', async () => {
  const identity = await projectIdentity(inRepo);
  const creates = [];
  const call = async (ref, args) => {
    if (ref === 'agents.create') { creates.push(args); return { id: 'new-' + args.name, name: args.name, status: 'idle' }; }
    throw new Error('unexpected ' + ref);
  };
  const ctx = { invocation: { extensionContext: { cwd: inRepo, sessionManager: { getSessionId: () => 'sess-1' } } }, call };
  const roleDir = join(tmpdir(), 'roles-');
  const built = await buildTriggers(ctx, { roleDir }, { hindsight_recall: async () => ({ details: { results: [] } }) }, []);
  assert.equal(built.desired.length, 6);
  assert.equal(creates.length, 6);
  for (const created of creates) {
    assert.equal(created.events.length, 0, 'no native subscriptions; component queues');
    assert.equal(created.residency, 'durable');
    assert.equal(created.responseMode, 'directive');
    assert.equal(created.triggerTurn, false, 'actors never steal the turn');
  }
  const again = await buildTriggers(ctx, { roleDir }, {}, built.desired.map(d => d.actor));
  assert.equal(again.desired.every(d => d.reused), true, 'second activation reuses durable actors');
  assert.equal(creates.length, 6, 'no duplicate creation');
  for (const [role, policy] of Object.entries(AUTO_ROLES)) assert.ok(STAGES[policy.stage].includes(role));
});

test('stage gating and scope keys bound duplicate work', () => {
  const child = { child: () => true, trusted: true };
  const untrusted = { child: () => false, trusted: false };
  const ok = { child: () => false, trusted: true };
  assert.equal(shouldTrigger('input', child), false);
  assert.equal(shouldTrigger('input', untrusted), false);
  assert.equal(shouldTrigger('input', ok), true);
  assert.equal(shouldTrigger('compact', ok), true);
  assert.equal(shouldTrigger('nope', ok), false);
  assert.equal(scopeKey('compact', 's1', 'cp1'), 'compact/s1/cp1');
  assert.equal(scopeKey('settled', 's1'), 'settled/s1/live');
});
