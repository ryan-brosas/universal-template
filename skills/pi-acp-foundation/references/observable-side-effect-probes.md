<!-- capsule-v2 -->
# Observable-side-effect probes — how do you smoke-test behavior whose proof lives outside the JSON-RPC channel (files on disk, internal queue depth)?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you smoke-test adapter behavior whose evidence is NOT in the protocol channel — artifacts written to disk, or internal state surfaced only through telemetry?

## smoke-export.mjs — diff-of-directory-listing as the assertion
**Path/Symbol:** `scripts/smoke-export.mjs` (whole, 51L).
**Signature:** `readdirSync(process.cwd()).filter(f => EXPORT_PATTERN.test(f))` before and after the `/export` turn; `EXPORT_PATTERN = /^pi-session-.*\.html$/`.
**Data Shape:** the assertion set is the DIFF `after.filter(f => !before.includes(f))` — pre-existing artifacts never satisfy the probe, so a stale file from an earlier run cannot produce a false green.

### Decisive source
```js
const before = readdirSync(process.cwd()).filter(f => EXPORT_PATTERN.test(f))
// …seed turn, then: session/prompt with '/export'…
const after = readdirSync(process.cwd()).filter(f => EXPORT_PATTERN.test(f))
const artifacts = after.filter(f => !before.includes(f))
assert(artifacts.length > 0, `no pi-session-*.html artifact created by /export (existing: ${JSON.stringify(before)})`)
const p = join(process.cwd(), artifacts[0])
const content = readFileSync(p, 'utf8')
assert(content.includes('<!DOCTYPE html>'), 'exported HTML missing doctype')
assert(content.includes('Session Export'), 'exported HTML missing session export title')
assert(content.length > 1_000, `exported HTML suspiciously small (${content.length} bytes)`)
unlinkSync(p)
```

**Flow:** snapshot cwd → seed a real turn → send `/export` as a prompt (the builtin dispatcher handles it) → re-list cwd → assert a NEW matching artifact exists → verify content (doctype, title, minimum size) → unlink the artifact so the probe leaves no residue. The probe reaches outside the JSON-RPC channel because the behavior's proof is a file on disk; the response alone (`stopReason: end_turn`) proves nothing.
**Invariant:** the diff (not the presence) is the assertion — pre-existing files are excluded by name; content is verified beyond existence (three content pins); the artifact is cleaned up so repeated runs stay green.
**Probe:** `node scripts/smoke-export.mjs` → `OK smoke-export (artifact <path> verified and cleaned up)`.

## smoke-queue.mjs — telemetry as the proof of serialization
**Path/Symbol:** `scripts/smoke-queue.mjs` (whole, 45L).
**Signature:** two `h.expectResult(...)` promises created BEFORE either is awaited; assertion on `h.updates.filter(u => u?._meta?.piAcp?.queueDepth === 0)`.
**Data Shape:** the adapter surfaces its client-side one-at-a-time queue depth as `session_info_update` `_meta.piAcp.queueDepth`; the probe treats a drained-to-0 observation as the proof.

### Decisive source
```js
// Fire both prompts before awaiting either: the adapter must queue the second.
const first = h.expectResult(3, 'session/prompt', { /* … */ }, { timeoutMs: 90_000 })
const second = h.expectResult(4, 'session/prompt', { /* … */ }, { timeoutMs: 90_000 })

const r1 = await first
const r2 = await second
assert(r1?.stopReason === 'end_turn', `first turn stopReason=${r1?.stopReason}`)
assert(r2?.stopReason === 'end_turn', `second turn stopReason=${r2?.stopReason}`)

// The adapter queue must drain back to 0 (session_info_update queueDepth).
const drained = h.updates.filter(u => u?._meta?.piAcp?.queueDepth === 0).length
assert(drained >= 1, 'no queueDepth:0 info update observed after the queued turns')
```

**Flow:** fire both prompts concurrently (both promises in flight before any await — the second MUST be queued by the adapter, not rejected) → await both, assert both end_turn → assert at least one `queueDepth: 0` info update was observed, proving the queue drained rather than silently dropping the second turn. The probe's comments state the boundary honestly: queue CONTROL semantics are pi-side; this probe proves the ADAPTER serializes concurrent ACP prompts and reports every JSON-RPC result.
**Invariant:** concurrency is created by promise ordering (fire-both-then-await), not by timing assumptions; the serialization proof is the adapter's own telemetry (queueDepth drained to 0), not an inference from response order.
**Probe:** `node scripts/smoke-queue.mjs` → `OK smoke-queue (2 concurrent prompts serialized end_turn; queueDepth drained to 0)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "smoke-export pi-session html artifact readdirSync queueDepth session_info_update concurrent prompts", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two reach-outside-the-channel techniques: diff-of-listing for filesystem side effects (snapshot, act, diff, verify content, clean up) and telemetry-observation for internal state (fire the concurrency, then assert the drained metric). Adapt the patterns and metric names to your protocol. Omit the pi-specific export format. Coverage caveat: zero prior leaf citations; complements adapter-builtin-slash-commands.md (the /export dispatcher) and turn-state-machine.md (the queue being observed) with the client-side proof techniques.
