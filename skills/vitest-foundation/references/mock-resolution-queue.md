<!-- capsule-v2 -->
# Mock resolution queue — how are queued vi.mock/vi.doMock registrations applied without ever reordering mock-vs-unmock effects?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** When mock calls are collected during collection/transform and applied later during module resolution, what preserves their relative order?

## Consecutive-action grouped drain
**Path/Symbol:** `packages/vitest/src/runtime/moduleRunner/bareModuleMocker.ts:BareModuleMocker.resolveMocks` (:150–184), `queueMock` (:295–308), `queueUnmock` (:310–316), `groupByConsecutiveAction` (:377–389); drain site `runtime/moduleRunner/startVitestModuleRunner.ts` (:159).
**Signature:** `static pendingIds: PendingSuiteMock[]`; `resolveMocks(): Promise<void>`; `queueMock(id: string, importer: string, factoryOrOptions?: MockFactory | MockOptions): void`.
**Data Shape:** `pendingIds` is a STATIC array on the class (one per worker runtime, shared across instances); each entry `{ action: 'mock' | 'unmock', id, importer, factory?, type }`. `getMockType` folds options into the type here (`function → manual`, `{spy:true} → autospy`, else `automock`) so the queue stores the final kind, not raw args.

### Decisive source
```ts
public async resolveMocks(): Promise<void> {
  if (!BareModuleMocker.pendingIds.length) { return }
  const resolveMock = async (mock: PendingSuiteMock) => { /* unmockPath or mockPath by action */ }
  // group consecutive mocks of the same action type together,
  // resolve in parallel inside each group, but run groups sequentially
  // to preserve mock/unmock ordering
  const groups = groupByConsecutiveAction(BareModuleMocker.pendingIds)
  for (const group of groups) {
    await Promise.all(group.map(resolveMock))
  }
  BareModuleMocker.pendingIds = []
}
```

**Flow:** `vi.mock`/`vi.doMock` during collection push onto `pendingIds` (no resolution yet) → every module resolution consults the queue first (`startVitestModuleRunner`: `if (VitestMocker.pendingIds.length) await moduleRunner.mocker.resolveMocks()`) → entries are split into runs of consecutive same-action entries; each run resolves its ids IN PARALLEL, runs execute SEQUENTIALLY → array reassigned to `[]` only after all groups finish. The native twin additionally drains inside `wrapDynamicImport` before any user dynamic import proceeds.
**Invariant:** mock/unmock ORDER is preserved between actions but NOT within a same-action run — `doUnmock(A); doMock(B); doUnmock(C)` may resolve A∥B then C, never C before A's unmock lands. Clearing must be a single post-drain reassignment (entries queued DURING the drain belong to the next batch). A porter who resolves each entry awaited-in-order loses the documented parallelism; one who fires all in parallel breaks interleaved doUnmock/doMock semantics.
**Probe:** `test/e2e/test/mocking.test.ts:325` — "doMock/doUnmock ordering is preserved in resolveMocks" runs 20 alternating `vi.doUnmock('/mock-lib-i'); vi.doMock('/mock-lib-i', …)` pairs and asserts every later `import('/mock-lib-i')` yields the mocked value.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "BareModuleMocker resolveMocks queueMock pendingIds", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the consecutive-action grouping drain and the resolve-time (not registration-time) application point gated on a cheap length check. Adapt where the drain hooks into your host's loader (resolution hook vs dynamic-import wrapper vs both). Omit the static-array-per-worker subtlety only if your host has exactly one mocker instance per process.
