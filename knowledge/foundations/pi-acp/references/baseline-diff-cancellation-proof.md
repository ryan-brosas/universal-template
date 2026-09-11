<!-- capsule-v2 -->
# Baseline-diff cancellation proof — how do you prove "streaming stopped after cancel" when you cannot see the stream, only the update log?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you prove that a mid-turn cancel actually stopped the stream — when the only observable is an append-only update log and there is no "stream closed" event?

## smoke-cancel.mjs — count before, cancel, count after
**Path/Symbol:** `scripts/smoke-cancel.mjs` (whole, 78L).
**Signature:** `h.waitForUpdate(predicate, { timeoutMs })` gates the streaming-start observation; `h.notify('session/cancel', { sessionId })` sends the cancel; the original `h.expectResult(3, 'session/prompt', …)` promise is awaited AFTER the notify.
**Data Shape:** the harness collects every `session/update` into `h.updates`; the probe filters `u?.sessionUpdate === 'agent_message_chunk'` and uses COUNTS as its only stream-activity signal.

### Decisive source
```js
// Baseline: startup info itself is delivered as an agent_message_chunk, so only
// Treat chunks arriving after session/new as proof that the model turn is streaming (P1-5 audit).
const baseline = h.updates.filter(u => u?.sessionUpdate === 'agent_message_chunk').length

const slow = h.expectResult(3, 'session/prompt', { /* long essay prompt */ }, { timeoutMs: 60_000 })
await h.waitForUpdate(() => h.updates.filter(u => u?.sessionUpdate === 'agent_message_chunk').length > baseline, {
  timeoutMs: 30_000
})
const before = h.updates.filter(u => u?.sessionUpdate === 'agent_message_chunk').length
assert(before > baseline, 'no model agent_message_chunk observed before cancel')

cancelSentAt = Date.now()
h.notify('session/cancel', { sessionId })
const result = await slow
assert(result?.stopReason === 'cancelled', `stopReason=${result?.stopReason}, expected cancelled`)

// Reject late updates: no new agent_message_chunk within 2s of cancellation.
const afterCancel = h.updates.filter(u => u?.sessionUpdate === 'agent_message_chunk').length
await new Promise(r => setTimeout(r, 2_000))
const later = h.updates.filter(u => u?.sessionUpdate === 'agent_message_chunk').length
assert(later === afterCancel, `late agent_message_chunk after cancel (${afterCancel} -> ${later})`)
```

**Flow:** (1) record the baseline chunk count at session/new completion — startup info itself arrives as an agent_message_chunk, so the baseline must be taken AFTER session/new or the assertion fires on startup noise; (2) fire the long prompt WITHOUT awaiting; (3) waitForUpdate until the count exceeds baseline — streaming has started; (4) snapshot `before`; (5) send cancel as a fire-and-forget NOTIFICATION (cancel has no response id — it is a JSON-RPC notification, not a request); (6) await the original prompt promise and assert `stopReason === 'cancelled'`; (7) sleep 2s and assert the count is UNCHANGED — no late chunks; (8) measure cancel latency (Date.now() delta) and report it in the OK line.
**Invariant:** the cancel is a notification (no response to await — the prompt promise is the only completion signal); the "no late updates" window is a bounded 2s settle, not an unbounded wait; the follow-up prompt gets a 120s budget because pi's abort lets the in-flight generation finish in the background (pi-side semantics, documented in the probe's comments — the probe tests the ADAPTER contract, not pi internals).
**Probe:** `node scripts/smoke-cancel.mjs` → `OK smoke-cancel (dist <hash>; N chunks before cancel; stopReason cancelled; cancel latency Xms; no late updates; follow-up end_turn)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "session/cancel agent_message_chunk baseline stopReason cancelled no late updates waitForUpdate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the baseline-diff pattern for any "did X stop" assertion over an append-only event log: snapshot before the action, act, bounded settle, assert the count is frozen. Adapt the 2s window and chunk filter to your protocol's update vocabulary. Omit the pi-specific abort semantics prose. Coverage caveat: zero prior leaf citations; complements turn-settling-hardening.md (which owns the adapter-side cancel path) with the client-side proof technique.
