<!-- capsule-v2 -->
# InterceptorsConsumer — how does an interceptor chain wrap the handler lazily, and what must survive a port?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** How are interceptors composed around one handler, why is nothing subscribed until someone subscribes, and where do async-context and teardown traps live?

## intercept / nextFn recursion
**Path/Symbol:** `packages/core/interceptors/interceptors-consumer.ts:intercept` (:10-35).
**Signature:** `async intercept<TContext>(interceptors: NestInterceptor[], args, instance, callback, next: () => Promise<unknown>, type?): Promise<unknown>`.
**Data Shape:** `interceptors` are already-resolved INSTANCES (global concat class-level concat method-level, upstream of this); `next` is the terminal handler thunk returning a Promise; return value is always an Observable.

### Decisive source
```ts
if (!interceptors || isEmptyArray(interceptors)) {
  return next();                                   // empty chain = plain call
}
const nextFn = async (i = 0) => {
  if (i >= interceptors.length) {
    return defer(AsyncResource.bind(() => this.transformDeferred(next)));
  }
  const handler: CallHandler = {
    handle: () => defer(AsyncResource.bind(() => nextFn(i + 1))).pipe(mergeAll()),
  };
  return interceptors[i].intercept(context, handler);   // lazy: only on subscribe
};
return defer(() => nextFn()).pipe(mergeAll());
```

**Flow:** empty-array shortcut returns `next()` directly → otherwise build index-closure `nextFn` → each interceptor receives a `handler.handle()` that advances to i+1 → terminal step defers `transformDeferred(next)` → whole chain wrapped in `defer(...).pipe(mergeAll())`.
**Invariant:** NOTHING runs until the returned Observable is subscribed — `intercept` methods fire at subscribe time, not at route creation (test pins "does not call `intercept` (lazy evaluation)"). `AsyncResource.bind` wraps every hop so AsyncLocalStorage state set in a guard/interceptor stays visible inside the deferred handler. `mergeAll()` appears exactly twice: once per `defer` level — dropping it turns the Observable-of-Observable into garbage results.
**Probe:** `packages/core/test/interceptors/interceptors-consumer.spec.ts` ("does not call `intercept` (lazy evaluation)" + "should allow an interceptor to set values in AsyncLocalStorage that are accessible from the controller").
**Coverage caveat:** none recorded.

## transformDeferred teardown gate
**Path/Symbol:** `packages/core/interceptors/interceptors-consumer.ts:transformDeferred` (:49-84).
**Signature:** `transformDeferred(next: () => Promise<any>): Observable<any>`.
**Data Shape:** consumes the terminal handler promise; emits its value or forwards errors via `subscriber.error`; teardown function unsubscribes the inner subscription.

### Decisive source
```ts
// Call next() eagerly here — invoked inside defer(AsyncResource.bind(...)), so the
// async context is correctly inherited. Deferring next() into the subscriber would
// lose it.
const nextPromise = next();
return new Observable(subscriber => {
  nextPromise.then(res => {
    if (subscriber.closed) { return; }   // consumer gone: NEVER subscribe producer
    innerSub = from(res instanceof Promise || res instanceof Observable ? res
                    : Promise.resolve(res)).subscribe(subscriber);
  }).catch(err => { if (!subscriber.closed) subscriber.error(err); });
  return () => { innerSub?.unsubscribe(); };
});
```

**Flow:** call `next()` EAGERLY (inside the bound async context) → when it resolves, check `subscriber.closed` BEFORE subscribing the produced Observable → if closed, skip entirely (no producer side effects, no teardown churn); else bridge promise/Observable into the outer subscriber.
**Invariant:** The `closed` check must precede subscription — subscribing just to unsubscribe in the same tick starts producer side effects only to abort them (SSE disconnect class bug, fixed here AND mirrored in RouterResponseController.sse). Errors arriving after close are swallowed, not rethrown.
**Probe:** `packages/core/test/interceptors/interceptors-consumer.spec.ts` "should not subscribe the producer Observable after the consumer has unsubscribed" (asserts both `subscribed` and `teardown` spies stay uncalled after unsubscribe-then-resolve).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "InterceptorsConsumer intercept transformDeferred", limit: 5 });
```

## Verdict
Adopt the lazy index-closure chain + eager-bound-terminal + closed-gate-before-subscribe trio as one unit; adapt the RxJS plumbing if your framework uses promises end-to-end (then the closed-gate becomes a cancellation-token check); omit `mergeAll` only if you drop Observable bridging. Porting wrong: eagerly calling every interceptor at creation time breaks request-scoped DI timing, and losing AsyncResource.bind silently breaks ALS-based tenancy/auth context.
