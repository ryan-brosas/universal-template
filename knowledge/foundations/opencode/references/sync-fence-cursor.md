<!-- capsule-v2 -->
# Sync fence cursor — how do you tell a mutating-request client exactly which event-sequence deltas it missed, and how do peers block until they have caught up?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** How can a server attach a compact "what changed" cursor to any mutation response so multi-client replicas can converge without streaming the whole log?

## Pre/post snapshot diff middleware
**Path/Symbol:** `packages/opencode/src/server/shared/fence.ts` (`HEADER` :8, `load` :11-21, `diff` :23-32, `parse` :34-52, `wait` :54-60) + `packages/opencode/src/server/routes/instance/httpapi/middleware/fence.ts` (whole, 25L).
**Signature:** `load(db, ids?) → Effect<Record<aggregateID, seq>>`; `diff(prev, next) → Record<id, seq>`; `parse(headers) → State | undefined`; `wait(workspaceID, state, signal?) → Effect<void, WaitForSyncError>`.
**Data Shape:** `State = Record<string, number>` over `EventSequenceTable(aggregate_id → seq)`; wire form is JSON in response header `x-opencode-sync`; missing ids use sentinel `-1`.

### Decisive source
```ts
// middleware/fence.ts — only mutating methods, only in workspace mode:
const ignoredMethods = new Set(["GET", "HEAD", "OPTIONS"])                       // :7
if (!Flag.OPENCODE_WORKSPACE_ID || ignoredMethods.has(request.method)) return yield* effect  // :15
const previous = yield* Fence.load(db)                                            // :17 snapshot BEFORE
const response = yield* effect                                                    // :18 run handler
const current = Fence.diff(previous, yield* Fence.load(db))                       // :19 re-load AFTER
if (Object.keys(current).length === 0) return response
return HttpServerResponse.setHeader(response, Fence.HEADER, JSON.stringify(current))  // :22
// shared/fence.ts:27 — deletion-aware diff with -1 sentinel:
.map((id) => [id, next[id] ?? -1] as const)
```

**Flow:** request (non-idempotent method, workspace flag on) ⇒ load full sequence state ⇒ execute handler ⇒ reload state ⇒ diff = entries whose seq moved (or vanished→-1) ⇒ empty diff passes response through unchanged; otherwise attach header. Consumer side: `parse` strictly filters to string keys + integer values and returns undefined on malformed JSON (never throws); `wait` delegates to `workspace.waitForSync(workspaceID, state, signal)` and is used by the proxy path of workspace-routing to hold remote-proxied responses until the local replica catches up.
**Invariant:** The fence is metadata, not authorization — it never fails the request. Diff must include deletions (-1). GET-family requests never pay the double-load cost. Parse must tolerate garbage headers silently.
**Probe:** `packages/opencode/test/server/httpapi-workspace-routing.test.ts:330-390` ("waits for sync fence headers from remote workspace HTTP responses" pins the consumer side end-to-end: remote responds `x-opencode-sync: {"aggregate":3}` → middleware called `waitForSync(workspaceID, {aggregate:3})`); source pin:
```bash
grep -n 'export const HEADER = "x-opencode-sync"' packages/opencode/src/server/shared/fence.ts
grep -n 'ignoredMethods' packages/opencode/src/server/routes/instance/httpapi/middleware/fence.ts
```
expect 1 + 1 hits.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "x-opencode-sync fence event sequence diff wait for sync", limit: 8 });
```

## Verdict
Adopt the pre/post-diff response-header cursor with strict client-side parsing and blocking wait; adapt the backing table (any monotonic per-aggregate sequence works) and gate flag; omit opencode's specific workspace sync loop.
