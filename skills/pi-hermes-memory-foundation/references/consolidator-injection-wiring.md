<!-- capsule-v2 -->
# Consolidator injection — how does the composition root give stores LLM consolidation power without importing a transport, and how must targets be remapped for project stores?

**Source:** pi-hermes-memory (MIT, `main@71beae8a53be2cdc4901744cf85bd65a1b3030e6`); Codebase Memory `pi-hermes-memory`. **Question:** Where do store-level overflow handlers get their expensive LLM capability from, and what target vocabulary must hold at the seam between stores, lock keys, and tool routing?

## Stores depend on an injected closure; project stores remap `memory → project`
**Path/Symbol:** `src/index.ts:runAutoConsolidation` (:251–272), consolidator installs (:274–281), `MemoryStore.setConsolidator` (`src/store/memory-store.ts:72–74`); warn gate `src/auto-consolidation-warning.ts:shouldWarnAutoConsolidationFailure` (:6–8).
**Signature:** `setConsolidator(fn: (target: "memory"|"user"|"failure", signal?: AbortSignal) => Promise<ConsolidationResult>)`.
**Data Shape:** `ConsolidationResult = { consolidated: boolean; deferred?: boolean; error?: string }`; store target vocabulary is 3-valued, tool/lock vocabulary is 4-valued (`+ "project"`).

### Decisive source
```ts
// src/index.ts:274-280 — identity map vs project remap
store.setConsolidator((target, signal) => runAutoConsolidation(target, store, target, signal));
configureProjectStore = (candidate) => {
  if (!candidate) return;
  candidate.setConsolidator((target, signal) =>
    runAutoConsolidation(target, candidate, target === "memory" ? "project" : target, signal),
  );
};
```

**Flow:** (1) the root builds ONE `runAutoConsolidation(target, targetStore, toolTarget, signal)` wrapper around `triggerConsolidation` (transport + lock ladder owned by consolidation-lock-ladder.md); (2) the global store gets it with `toolTarget = target` identity; (3) every project store gets a closure that remaps ONLY `"memory"→"project"` so lock keys and prompt routing name the project scope while the store keeps its internal 3-value vocabulary; (4) rebinding installs the same closure on each new candidate and no-ops on null. Logging gates in the wrapper: `deferred ⇒ console.info` always; failure ⇒ `console.warn` only through `shouldWarnAutoConsolidationFailure(config.autoConsolidateWarnOnFailure, result.consolidated)` (#135 — keep failures visible in tool results; session-console warnings separately configurable).
**Invariant:** a store must never import or construct a transport — capability arrives as a settable closure, so tests can inject fakes and the transport can change freely; the `memory→project` remap is the single translation point between store vocabulary and tool/lock vocabulary, and dropping it makes project consolidation contend on global lock keys.
**Probe:** `tests/index.test.ts` pins the warn truth table (`(true,false)→warn`, `(false,false)→silent`, `(·,true)→never`), executed GREEN pre-write: 3 passed / 0 failed; `tests/handlers/auto-consolidate.test.ts:412` "can consolidate project memory using the project tool target" within the suite run (35 passed / 0 failed). Coverage: cited paths `no_recorded_issue` @ gen 2026-08-24T14:05:19Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "runAutoConsolidation setConsolidator shouldWarnAutoConsolidationFailure triggerConsolidation configureProjectStore", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt setter-injected capability with a single target-vocabulary translation point at install time. Adapt the vocabularies and the warn-gate config key to your host; omit the console gates if your host has structured logging hooks. Caveat: the remap itself has no dedicated upstream unit test — it is pinned indirectly by :412 plus the lock-key tests in consolidation-lock-ladder.md's probe list.
