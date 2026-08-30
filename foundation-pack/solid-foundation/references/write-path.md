<!-- capsule-v2 -->
# Solid write path — how does a signal set fan out STALE vs PENDING marks without running anything?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid` (pass-3 refresh from retired `ext-solid` @ identical pin). **Question:** When a setter fires, how are downstream computations marked for update, and why must writes never run computations inline?

## writeSignal: mark-then-queue with pure/effects split
**Path/Symbol:** `packages/solid/src/reactive/signal.ts:writeSignal` (:1341-1376) + helper `markDownstream` (:1686-1698).
**Signature:** `export function writeSignal(node: SignalState<any> | Memo<any>, value: any, isComp?: boolean)` — `isComp: true` only from `runComputation`'s internal memo publish.
**Data Shape:** `STALE = 1`, `PENDING = 2` (ComputationState). `Updates` = queue of pure (memo/computed) nodes; `Effects` = queue of non-pure. Transition twins: `tValue`/`tState` shadow `value`/`state`.

### Decisive source
```ts
if (!node.comparator || !node.comparator(current, value)) {
    ...
    if (node.observers && node.observers.length) {
      runUpdates(() => {
        for (let i = 0; i < node.observers!.length; i += 1) {
          const o = node.observers![i];
          if (TransitionRunning && Transition!.disposed.has(o)) continue;
          if (TransitionRunning ? !o.tState : !o.state) {
            if (o.pure) Updates!.push(o);
            else Effects!.push(o);
            if ((o as Memo<any>).observers) markDownstream(o as Memo<any>);
          }
          if (!TransitionRunning) o.state = STALE;
          else o.tState = STALE;
        }
        if (Updates!.length > 10e5) {
          Updates = [];
          if (IS_DEV) throw new Error("Potential Infinite Loop Detected.");
          throw new Error();
        }
      }, false);
    }
}
```

**Flow:** comparator gate (default `equalFn` reference equality; `{ equals: false }` always writes) → store value (`tValue` if transition owns the source, plus committed `value` when not running) → direct observers get `state = STALE` and are queued by purity → each queued memo's own observers get `state = PENDING` via `markDownstream` recursion → the enclosing `runUpdates` drains later.
**Invariant:** Writes only MARK (STALE = will re-run, PENDING = ancestor stale, may be skipped); execution happens exclusively in the queue drain (`runTop`). A memo whose value doesn't change still runs but never re-marks its own observers — equality short-circuits propagation at run time, not write time. The 1,000,000-entry Updates cap is the infinite-loop backstop ("Potential Infinite Loop Detected." in dev).
**Probe:** `grep -c 'if (o.pure) Updates!.push(o);' packages/solid/src/reactive/signal.ts` → `2` (writeSignal + createSelector); companion `grep -c 'else Effects!.push(o);'` → `2`. Behavior pinned by `test/signals.memo.spec.ts` "does not trigger downstream computations unless changed" (:125-145): `{equals:false}` upstream + unchanged memo output ⇒ downstream runs 0 times.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "writeSignal markDownstream STALE PENDING", limit: 10 });
```

## Verdict
Adopt mark-vs-run separation and the two-state (STALE/PENDING) marking lattice — this is what makes diamond graphs evaluate each node once. Adapt the module-global queues into a scheduler object for multi-instance hosts. Omit transition branches if you have no transitions.
