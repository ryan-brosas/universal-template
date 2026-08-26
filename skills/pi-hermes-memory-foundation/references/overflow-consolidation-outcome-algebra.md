<!-- capsule-v2 -->
# Overflow consolidation outcome algebra — when an add hits the char ceiling under auto-consolidate, which exact outcome messages must reach the model for each consolidation result?

**Source:** pi-hermes-memory (MIT, `main@71beae8a53be2cdc4901744cf85bd65a1b3030e6`); Codebase Memory `pi-hermes-memory`. **Question:** How does a store turn one failed write into a bounded retry-with-consolidation ladder whose every terminal state is a distinct, actionable error string?

## Capacity errors are recognized by their `"Memory at "` prefix and end in five distinct suffixes
**Path/Symbol:** `src/store/memory-store.ts:MemoryStore.addWithConsolidation` (:256–313); injector seam `setConsolidator` (:72–74).
**Signature:** `private addWithConsolidation(target, content, signal, retriesLeft, addedMessage, project?): Promise<MemoryResult>` — recursive with exactly ONE retry.
**Data Shape:** input `ConsolidationResult {consolidated, deferred?, error?}`; output `MemoryResult` whose failure shape is always `{ success: false, error: <capacity error> + <one outcome suffix> }`.

### Decisive source
```ts
// src/store/memory-store.ts:263-273 — the guard chain and its sentinel
if (result.success || retriesLeft <= 0
    || this.memoryOverflowStrategy() !== "auto-consolidate"
    || !this.consolidator
    || !result.error?.startsWith("Memory at ")) return result;
if (this.overflowGraceActive(target)) return { ...result,
  error: `${result.error} Automatic consolidation is deferred for ${this.overflowGraceMs()}ms …` };
// #135: every failure mode used to be swallowed and present identically to a plain capacity error
const consolidation = await this.consolidator(target, signal).catch(
  (err): ConsolidationResult => ({ consolidated: false, error: `consolidator threw ${String(err).slice(0, 200)}` }));
```

**Flow:** (1) `_add` fails at capacity producing an error starting `"Memory at "`; (2) guard chain exits unless strategy=auto-consolidate ∧ consolidator set ∧ retries remain ∧ prefix matches — the PREFIX is the routing sentinel, so unrelated errors never trigger consolidation; (3) active overflow-grace ⇒ defer-with-manual-first suffix (clock owned by overflow-grace-window.md); (4) consolidator invocation is exception-normalized (`consolidator threw …`); (5) outcome algebra: `deferred` ⇒ "Another session is consolidating '<target>' right now, so this entry was not saved — retry in a moment." (#144 consumer side); `!consolidated` ⇒ "Auto-consolidation attempted but failed: <reason>"; reload-after-success failure ⇒ "succeeded but reloading memory failed"; success ⇒ `loadFromDisk()` then ONE recursive retry with `retriesLeft - 1`; retry still capacity-blocked ⇒ "Auto-consolidation ran but did not free enough space."
**Invariant:** every terminal state carries a DIFFERENT actionable suffix (retry-ask vs reason vs freed-nothing vs grace-clock), the original capacity error is always preserved as the prefix, and consolidation runs at most once per add — no loops.
**Probe:** `tests/handlers/auto-consolidate.test.ts` — :915 surfaces reported reason, :931 reasonless failure named, :939 deferred asks for retry instead of reporting failure, :957 throwing consolidator surfaced, :969 ran-but-freed-nothing distinguished (:788 trigger / :835 strategy-off skip / :866 no-consolidator skip); suite executed GREEN pre-write: 35 passed / 0 failed. `tests/store/memory-store.test.ts` :187/:207/:232/:261/:291 pin reject-strategy, grace deferral/expiry/clearing; suite GREEN: 91 passed / 0 failed. Coverage: both paths `no_recorded_issue` @ gen 2026-08-24T14:05:19Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "addWithConsolidation Memory at deferred consolidated retriesLeft overflowGrace", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the sentinel-prefix guard chain plus the five-suffix outcome vocabulary and single-retry bound. Adapt message wording and the ConsolidationResult shape to your host's tool-result contract. Omit the grace branch only if you port overflow-grace-window.md's clock too. Caveat: suffix strings are UX contracts pinned by test regexes (`/test consolidation/`, reason assertions) rather than exact-equality snapshots.
