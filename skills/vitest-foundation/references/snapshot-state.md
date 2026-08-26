<!-- capsule-v2 -->
# Snapshot state machine — how does a snapshot engine decide write vs match vs delete per assertion, keyed by test name + invocation count?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** What is the reconcile rule that turns (pass, hasSnapshot, updateSnapshot mode, CI) into matched/added/updated/unmatched — and how do retries and obsolete keys work?

## SnapshotState
**Path/Symbol:** `packages/snapshot/src/port/state.ts:SnapshotState` (64–629) — `_reconcile` (311–396), `match` (473–563), `save` (398–438), `pack` (601–628), `clearTest` (159–182), key derivation in `port/utils.ts` (`testNameToKey`, `addExtraLineBreaks`); summary roll-up in `manager.ts:emptySummary/addSnapshotResult` (44–97).
**Signature:** `static async create(testFilePath, options)` → reads the snap file via the pluggable `snapshotEnvironment`; `match({ testId, testName, received, isInline?, error?, rawSnapshot? }) → { actual, count, expected, key, pass }`.
**Data Shape:** keys are `` `${testName} ${count}` `` (count = per-testName invocation counter via `CounterMap`); `_uncheckedKeys` starts as every stored key; three storage kinds: external `_snapshotData[key]`, inline `_inlineSnapshots` (stack-position located), raw `_rawSnapshots`; `updateSnapshot: 'all' | 'new' | 'none'`.

### Decisive source
```ts
// These are the conditions on when to write snapshots:
//  * There's no snapshot file in a non-CI environment.
//  * There is a snapshot file and we decided to update the snapshot.
//  * There is a snapshot file, but it doesn't have this snapshot.
// These are the conditions on when not to write snapshots:
//  * The update flag is set to 'none'.
//  * There's no snapshot file or a file without this snapshot on a CI environment.
if ((opts.hasSnapshot && this._updateSnapshot === 'all')
  || ((!opts.hasSnapshot || !opts.snapshotIsPersisted)
    && (this._updateSnapshot === 'new' || this._updateSnapshot === 'all'))) {
  ...increment updated/added counters; _addSnapshot(...)
  return { actual: '', expected: '', key, count, pass: true }   // writes always "pass"
}
else if (!opts.pass) { this.unmatched.increment(testId); return { pass: false, ... } }
else { this.matched.increment(testId); return { pass: true } }
```
Retry support (`clearTest`) and the refresh-on-pass subtlety:
```ts
if (pass && !isInline && !raw) {
  // re-saving the file can lose proper escaping through the JS round-trip:
  // refresh in-memory data with the freshly serialized string so the file is written correctly
  this._snapshotData[key] = receivedSerialized
}
```

**Flow:** `create()` loads existing file into `_snapshotData` (+ `_initialData` copy) with all keys unchecked → each `match()` increments the testName counter to build the key, deletes it from unchecked, serializes received (`serialize` + extra line breaks), compares trimmed strings, routes through `_reconcile` → test-level `clearTest(testId)` (called on every retry attempt by the runner's `onBeforeTryTask`) restores initial data for that test's keys and decrements counters → end of file: `pack()` removes still-unchecked keys when updating, `save()` writes external/inline/raw snapshots or DELETES an empty file under `'all'`.

**Invariant:** (1) a missing snapshot passes-and-writes only outside CI or in update modes — CI without a stored snapshot fails; (2) keys are name+ordinal so repeated assertions in one test map to distinct snapshots; (3) inline snapshots are located by parsed stack position with a column-1 correction and reject two DIFFERENT values at one location; (4) retries must reset state per attempt or attempt N would collide with stale counts.

**Probe:** e2e `test/e2e/test/snapshot.test.ts`; unit `test/unit/test/snapshot-file.test.ts` (:25 handle empty file), `moved-snapshot.test.ts`, `snapshot-async.test.ts`, `inline-snap.test.ts`. Coverage caveat: probes read on disk at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "SnapshotState _reconcile clearTest pack updateSnapshot", limit: 10, fields: ["signature", "name", "file"] });
// resolves: vitest.packages.snapshot.src.port.state.SnapshotState / .client.SnapshotClient
```

## Verdict
Adopt the counter-keyed state machine, the documented write/match reconcile table, per-test state reset for retries, and empty-file deletion semantics. Adapt serialization and environment I/O (the `snapshotEnvironment` indirection exists so browser workers can participate). Omit domain-template adapters (`domain.ts` pattern snapshots), raw-snapshot CRLF normalization details, and jest-image-snapshot compat getters unless required.
