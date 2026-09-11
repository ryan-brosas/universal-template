<!-- capsule-v2 -->
# GuardsConsumer — sequential short-circuit authorization over three return shapes

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** In what order do guards run, what return types are legal, and where does the first false stop execution?

## tryActivate / pickResult
**Path/Symbol:** `packages/core/guards/guards-consumer.ts:tryActivate` (:8-35), `pickResult` (:49-56).
**Signature:** `async tryActivate<TContext>(guards: CanActivate[], args, instance, callback, type?): Promise<boolean>`; `pickResult(result: boolean | Promise<boolean> | Observable<boolean>): Promise<boolean>`.
**Data Shape:** `guards` are resolved instances (global + class + method concat done by GuardsContextCreator); each `canActivate(context)` may return boolean, Promise&lt;boolean&gt;, or Observable&lt;boolean&gt;.

### Decisive source
```ts
if (!guards || isEmptyArray(guards)) {
  return true;
}
const context = this.createContext(args, instance, callback);
context.setType<TContext>(type!);
for (const guard of guards) {          // SEQUENTIAL, declaration order
  const result = guard.canActivate(context);
  if (typeof result === 'boolean') {
    if (!result) return false;         // sync fast path
    continue;
  }
  if (await this.pickResult(result)) continue;
  return false;                        // first falsy stops everything
}
return true;
```

**Flow:** empty array → true (no context built) → build ONE ExecutionContextHost shared by all guards → loop guards in order → sync boolean short-circuits without awaiting → async/Observable results go through `pickResult` (Observable via `lastValueFrom`) → first falsy returns false immediately.
**Invariant:** Guards NEVER run in parallel and later guards don't run after a failure — a porter who "optimizes" to `Promise.all` changes side-effect order and lets every guard's ALS writes race. The same host instance is reused across guards so `switchToHttp()` mutations are visible downstream. Observable guards resolve to their LAST emitted value.
**Probe:** `packages/core/test/guards/guards-consumer.spec.ts` ("should return false" when at least one guard returns false; "should keep local storages accessible" pins ALS visibility across the guard loop).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "GuardsConsumer tryActivate pickResult", limit: 5 });
```

## Verdict
Adopt strict sequential short-circuit with the three-shape return ladder; adapt the Observable branch away if you have no RxJS (keep boolean/Promise); omit context sharing only if your guards are pure. Porting wrong: parallelizing guards or continuing after a false breaks auth semantics that tests pin at the consumer level.
