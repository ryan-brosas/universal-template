<!-- capsule-v2 -->
# Constructor resolution — how are constructor params resolved concurrently yet safely when dependencies resolve in any order?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** Why must every param signal a Barrier before instance creation is decided, and how do optional deps and the INQUIRER token fit?

## Injector.resolveConstructorParams
**Path/Symbol:** `packages/core/injector/injector.ts:Injector.resolveConstructorParams` (307-418; param loop 338-415).
**Signature:** `resolveConstructorParams(wrapper, moduleRef, inject, callback(instances, depth), resolutionContext?, parentInquirer?): Promise<void>`.
**Data Shape:** `dependencies: InjectionToken[]` (from Reflect metadata or factory `inject`), `optionalDependenciesIds: number[]`; per-param closure mutates shared `isResolved`/`depth`.

### Decisive source
```ts
const paramBarrier = new Barrier(dependencies.length);
const resolveParam = async (param, index) => {
  try {
    if (this.isInquirer(param, parentInquirer)) {
      paramBarrier.signal();            // INQUIRER contributes no wrapper — still count it!
      return parentInquirer && parentInquirer.instance;
    }
    ...
    const paramWrapper = await this.resolveSingleParam(...);
    // ALL wrappers must be resolved BEFORE evaluating tree staticity,
    // otherwise undefined/null injection results
    await paramBarrier.signalAndWait();
    ...
    if (!instanceHost.isResolved && !paramWrapperWithInstance.forwardRef) isResolved = false;
    return instanceHost?.instance;
  } catch (err) {
    paramBarrier.signal();              // release siblings on failure too
    const isOptional = optionalDependenciesIds.includes(index);
    if (!isOptional) throw err;
    return undefined;                   // optional dep failures degrade to undefined
  }
};
const instances = await Promise.all(dependencies.map(resolveParam));
isResolved && (await callback(instances, depth));   // callback SKIPPED unless fully static-resolved
```

**Flow:** gather dependency tokens → map `resolveParam` concurrently → each param resolves its wrapper, then rendezvous at the barrier → only if every dependency ended resolved does the instantiation `callback` run.
**Invariant:** The Barrier count equals `dependencies.length` including optional and INQUIRER params; both the success path (`signalAndWait`) and error path (`signal` in catch) must release it or sibling awaits hang forever. The same pattern repeats for property injection in `resolveProperties` with `propertyBarrier`.
**Probe:** `packages/core/test/injector/injector.spec.ts::resolveConstructorParams` + `packages/core/test/helpers/barrier.spec.ts`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "resolveConstructorParams paramBarrier signalAndWait", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt concurrent param resolution gated by an all-participants barrier before any ordering-sensitive evaluation; adapt barrier granularity to your resolver; omit transient root-inquirer inheritance if you have no transient scope. Porting wrong: awaiting params serially works but loses the deadlock-freedom guarantee when one param's INQUIRER token would never be signaled.
