<!-- capsule-v2 -->
# Solid batch & transitions — how does runUpdates nest, and how do transitions defer writes via tValue shadowing?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid` (pass-3 provenance refresh: originally authored against the retired `ext-solid` graph at the identical pin; retrieval re-executed on `solid` 2026-08-25, gen 2026-08-25T20:12:15Z). **Question:** What is the exact re-entrancy contract of `runUpdates`, and what state does a transition keep per-source?

## runUpdates nesting + completeUpdates transition commit
**Path/Symbol:** `packages/solid/src/reactive/signal.ts:runUpdates` (:1556-1572), `completeUpdates` (:1574-1622), `startTransition` (:1082-1111).
**Signature:** `function runUpdates<T>(fn: () => T, init: boolean)` — `init: true` from roots/`runWithOwner`, `false` from batch/writes; `startTransition(fn): Promise<void>`.
**Data Shape:** `TransitionState { sources: Set<SignalState>, effects: Computation[], promises: Set, disposed: Set, queue: Set, running, done?, resolve? }`. Globals `Updates/Effects/ExecCount`.

### Decisive source
```ts
function runUpdates<T>(fn: () => T, init: boolean) {
  if (Updates) return fn();            // nested call: join outer batch
  let wait = false;
  if (!init) Updates = [];
  if (Effects) wait = true;
  else Effects = [];
  ExecCount++;
  try {
    const res = fn();
    completeUpdates(wait);
    return res;
  } catch (err) {
    if (!wait) Effects = null;
    Updates = null;
    handleError(err);
  }
}
```

**Flow:** nested `runUpdates` calls (batch inside effect inside root) simply execute `fn` — only the OUTERMOST call owns queue draining. At drain: pure `Updates` run first (`runQueue`→`runTop`); then if a Transition has pending promises, park remaining effects in `Transition.effects`, set `running=false`, flip `transPending(true)` and return early; when the last promise resolves, the finish block commits atomically: for every source in `Transition.sources`, `v.value = v.tValue`, promote `tOwned → owned`, delete tValue/tState, clean disposed nodes, resolve `done`.
**Invariant:** Reads during a transition return `tValue` ONLY for sources registered in `Transition.sources` (`readSignal` :1337); writes to already-transitioning sources update `tValue` and skip committing `value` until the finish block. This is why `createSignal`'s setter checks `Transition.sources.has(s)` before calling the updater fn (:252-258). A second `startTransition` while one runs joins it and returns its existing `done` promise.
**Probe:** `grep -c 'v.value = v.tValue;' packages/solid/src/reactive/signal.ts` → `1`. Decisive test ranges: `test/signals.spec.ts:817-845` "selection made inside a transition" — line :818-819 is load-bearing (`// startTransition only creates a real Transition once a SuspenseContext exists` + bare `getSuspenseContext()` call): without a Suspense context, startTransition creates NO Transition object at all, so the whole shadow-commit path is only exercised under Suspense; after `await startTransition(() => set(1))` exactly ONE memo reran (count===1 — createSelector's equality gate held across the commit), and the second transition reran exactly TWO (deselect old + select new). Pass-2's citation "signals.spec (:817+)" named this range; no `test/transition.spec.ts` exists at this pin (pass-3 correction). **Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "runUpdates completeUpdates startTransition tValue", limit: 10 });
```

## Verdict
Adopt outermost-owner batching + shadow-value transition commit. Adapt the microtask-based `Promise.resolve().then` kickoff to your host scheduler. Omit `scheduleQueue`/`Scheduler` unless porting `enableScheduling` time-slicing (see scheduler capsule).
