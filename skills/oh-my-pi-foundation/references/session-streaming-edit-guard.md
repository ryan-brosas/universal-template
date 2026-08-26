<!-- capsule-v2 -->
# Streaming edit guard dual-epoch invalidation — how do queued async validations of a streamed edit avoid judging stale file state after an edit lands or a turn resets?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** What is the full staleness-defense choreography (turn epoch + per-file epoch + promise-identity check) that lets fire-and-forget removed-lines checks abort bad streamed edits without ever aborting on outdated content?

## StreamingEditGuard staleness defense
**Path/Symbol:** `packages/coding-agent/src/session/stream-guards.ts:` `StreamingEditGuard` (39–349); staleness core in `#checkRemovedLines` (:250–292) and `#queueRemovedLinesCheck` (:295–320); reset/invalidate at (:75–84)/(:118–125).
**Signature:** `class StreamingEditGuard { preCache(event: AgentEvent): void; maybeAbort(event: AgentEvent): void; invalidate(filePath: string): void; reset(): void; get abortTriggered(): boolean }`.
**Data Shape:** `#fileCache: Map<path, Promise<string|undefined>>` (LF-normalized text; read failures cache `undefined` so ENOENT doesn't re-read per delta tick); `#confirmedRemovedLines: Map<path, Set<string>>`; `#verificationChain: Map<path, Promise<void>>`; `#fileEpoch: Map<path, number>`; `#epoch: number` (turn-scoped, bumped by `reset()`).

### Decisive source
```ts
// Per-file invalidation token: queued checks from before an edit result must
// not validate their old diff against the newly written file.
#fileEpoch = new Map<string, number>();
// Internal invalidation token, bumped by reset(). Unlike the session's
// promptGeneration — which only advances on abort/session-reset — this moves
// at every turn boundary, so a removed-lines check queued before reset()
// cannot start under the next turn and abort it on the previous edit.
#epoch = 0;

const cached = this.#ensureFileCache(resolvedPath);
const content = await cached;
if (content === undefined || this.#abortTriggered) return;
// Cache was invalidated (edit landed / turn reset) while loading: drop this
// stale evaluation rather than judging outdated content.
if (this.#fileCache.get(resolvedPath) !== cached) return;
```

**Flow:** streaming toolcall deltas → `preCache` primes `#fileCache` (only when `edit.streamingAbort`) → `maybeAbort` slices the diff to complete lines, normalizes, deobfuscates, extracts `-` lines → `#queueRemovedLinesCheck` snapshots BOTH epochs, chains behind the per-file verification chain → after the await, a check proceeds only if not aborted AND turn `#epoch` unchanged AND per-file `#fileEpoch` unchanged AND cached promise identity unchanged → each unconfirmed removed line is `content.includes()`-scanned with a 2 ms time-slice (`Bun.sleep(0)` re-checks both epochs mid-slice) → any miss calls `#abortPatch` (sets flag + `agent.abort()`).
**Invariant:** A queued validation must never judge content newer than its snapshot: three independent tokens (turn epoch, file epoch, promise identity) must all match or the check silently drops. The edit tool itself re-verifies before applying — the guard is advisory-only, so a dropped check is safe but a false abort kills a good turn (the race fixed by resetting the guard BEFORE async event fan-out, `agent-session.ts:2549-2551`).
**Probe:** `test/streaming-edit-abort.test.ts` pins both races: `"drops a queued removed-lines verification whose turn was reset before it started"` (held-load mock proves reset() drops the late verdict) and `"drops queued removed-lines verifications when the edited file is invalidated"` (asserts exactly ONE target read via `targetReads === 1`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "StreamingEditGuard removed lines verification epoch invalidation", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: `StreamingEditGuard.#checkRemovedLines stream-guards.ts:250-292`, `.#queueRemovedLinesCheck :295-320`.

## Verdict
Adopt the triple-token staleness defense (epoch+epoch+promise-identity), the failure-caching file promise, the 2 ms time-sliced scans, and reset-before-fan-out ordering. Adapt the host seams (`StreamGuardsHost`, Bun.file). Omit nothing here — every piece is load-bearing. Runner caveat: pi-natives napi build blocks bun test in this environment (needs nightly Rust); probes verified as byte-exact greps against the pinned test titles instead of execution.
