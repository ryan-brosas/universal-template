<!-- capsule-v2 -->
# Settlement signal + pending join — how does a concurrent second request for the same provider wait for, or detect cycles in, an in-flight instantiation?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What makes parallel resolution of one wrapper safe, and how is a circular dependency distinguished from a legitimate wait?

## Injector.loadInstance / SettlementSignal
**Path/Symbol:** `packages/core/injector/injector.ts:Injector.loadInstance` (134-220); `packages/core/injector/settlement-signal.ts:SettlementSignal` (1-59).
**Signature:** `loadInstance(wrapper, collection, moduleRef, resolutionContext?): Promise<void>`; `settlementSignal.isCycle(wrapperId): boolean`.
**Data Shape:** `instanceHost.donePromise: Promise<unknown>` resolves with an optional error value; `SettlementSignal._refs: Set<wrapperId>` tracks dependencies the host is currently waiting on.

### Decisive source
```ts
if (instanceHost.isPending) {
  const settlementSignal = wrapper.settlementSignal;
  // A cycle exists only if the PENDING target lists ME as its dependency
  if (resolutionContext.inquirer && settlementSignal?.isCycle(resolutionContext.inquirer.id)) {
    throw new CircularDependencyException(`"${wrapper.name}"`);
  }
  return instanceHost.donePromise!.then((err?) => { if (err) throw err; });  // join, don't reload
}
...
} catch (err) {
  wrapper.removeInstanceByContextId(...);  // roll back the half-created entry
  settlementSignal.error(err);             // wake every waiter WITH the error
  throw err;
}
```

```ts
// SettlementSignal — resolve-style settle; err travels as the resolved VALUE
public insertRef(wrapperId: string) { this._refs.add(wrapperId); }
public isCycle(wrapperId: string) { return !this.completed && this._refs.has(wrapperId); }
```

**Flow:** loadInstance → applySettlementSignal (mark pending, publish donePromise) → resolve deps (`resolveComponentHost.insertRef(depId)` records edges) → instantiate → `complete()`. Concurrent callers hit `isPending`, either join the promise or throw CircularDependency.
**Invariant:** Waiters must rethrow the settled error value (the promise RESOLVES with err rather than rejecting). On failure the half-written context entry is removed BEFORE settling so later requests retry cleanly. `isCycle` requires `!completed` — a finished provider never reports cycles.
**Probe:** `packages/core/test/injector/injector.spec.ts::loadInstance` (pending/error paths).
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "SettlementSignal isCycle donePromise loadInstance pending", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-attempt settlement signal (pending flag + joinable promise + ref-set cycle detection + rollback-on-error); adapt error propagation to rejection style if you control all waiters; omit ref-tracking when your graph cannot cycle. Porting wrong: naively queueing concurrent loads re-runs constructors or deadlocks on circular imports.
