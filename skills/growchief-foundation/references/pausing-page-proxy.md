<!-- capsule-v2 -->
# Pausing-page proxy — how would a Page object gain pause/resume + audit logging via Proxy, and why is it disabled here?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** the cursor wraps `page` with `createPageWrapper` — what behavior would it add, and what actually ships?

## Proxy handler gates async methods on a pause BehaviorSubject — currently bypassed by an early return
**Path/Symbol:** `shared/server/bots/pausing.page.ts:createPageWrapper` (:10-66); consumer `bot.cursor.ts:44-49`; pause controls `SpecialEvents.pause()/resume()` (bots.interface.ts).
**Signature:** `createPageWrapper(page, pauseSubject: BehaviorSubject<boolean>, pause$: Observable<any>, saveLog$) → Page`.
**Data Shape:** `pauseSubject.value` is the live gate; `firstValueFrom(pause$.pipe(filter(paused => !paused)))` is the resume await.

### Decisive source
```ts
return page;                       // ← FIRST LINE AFTER DESTRUCTURE: wrapper disabled
async function waitIfPaused() {
  if (pauseSubject.value)
    await firstValueFrom(pause$.pipe(filter((paused) => !paused)));
}
const handler = { get(target, prop) {
  const origProp = target[prop];
  if (typeof origProp === 'function') {
    if (target[prop].constructor.name !== 'AsyncFunction')
      return (...args) => origProp.apply(target, args);      // sync passthrough
    return async (...args) => {
      saveLog$.next({ message: String(prop), args, type: 'info' }); // method audit
      await waitIfPaused();                                   // gate BEFORE call
      while (true) {
        try { return await origProp.apply(target, args); }
        catch (err) {
          if (pauseSubject.value) { await waitIfPaused(); continue; } // paused mid-error ⇒ retry
          throw err;                                          // real error propagates
        }
      }
    };
  }
  ... return origProp;
}};
return new Proxy(page, handler);
```

**Flow (as designed):** every async Page call logs name+args → waits while paused → executes → if it fails WHILE a pause was requested, wait for resume and retry once path instead of surfacing a half-applied action.
**Invariant:** the sync/async split matters — only AsyncFunction-typed methods are wrapped (checking `constructor.name === 'AsyncFunction'`), so property reads and sync helpers keep identity semantics. The unconditional `return page;` above the Proxy construction means at HEAD `abb1e37a` NO page is wrapped: pause/resume subjects exist and are flipped by `cursor.pause()/resume()`, but nothing observes them in the page path.
**Probe:** no test runner upstream. Deterministic pins: `grep -n 'return page;' shared/server/bots/pausing.page.ts` → :16; `grep -n 'AsyncFunction' shared/server/bots/pausing.page.ts` → :28.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "createPageWrapper pauseSubject", limit: 5 });
```

## Verdict
Adopt the proxy-gate pattern for pausable automation drivers (audit log + pre-call gate + paused-failure retry). ADAPT: remove the early return to enable it; note constructor.name breaks under minification — feature-detect differently in bundled builds.
