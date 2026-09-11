<!-- capsule-v2 -->
# withDoc throttle funnel — how do you compose auth middleware, usage throttling, and doc loading without leaking a concurrency slot?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the correct layering order for per-document API limits, and where exactly must the release happen?

## throttled(withDoc(cb)) — acquire increments BEFORE limit checks, release sits in finally around everything
**Path/Symbol:** `app/server/lib/DocApi.ts:addEndpoints` `const withDoc` (:189); `app/server/lib/DocApiUsageTracker.ts:throttle` (:95–113), `acquire` (:60–75), `release` (:79), `_checkAndUpdateDailyUsageExceeded` (:119–150).
**Signature:** `withDoc = (callback: WithDocHandler) => throttled(this._requireActiveDoc(callback))`; `acquire(docId: string, dailyMax: number | undefined): void`; `release(docId: string): void`.
**Data Shape:** dailyMax comes from billing features per request: `req.docAuth.cachedDoc.workspace.org.billingAccount?.getEffectiveFeatures().baseMaxApiUnitsPerDocumentPerDay`. Parallel cap is a tracker-level constant (0 = unlimited). Counters keyed by raw docId string.

### Decisive source
```ts
public throttle(callback: Handler): RequestHandler {
    return async (req, res, next) => {
      const docId = getDocId(req);
      try {
        const doc = (req as RequestWithLogin).docAuth!.cachedDoc!;
        const dailyMax = doc.workspace.org.billingAccount
          ?.getEffectiveFeatures().baseMaxApiUnitsPerDocumentPerDay;
        this.acquire(docId, dailyMax);            // may throw ApiError(429)
        await callback(req as RequestWithLogin, res, next);
      } catch (err) {
        next(err);
      } finally {
        this.release(docId);                      // ALWAYS, even on 429
      }
    };
}
// acquire(): "The parallel counter is incremented unconditionally before checking limits,
//  so callers MUST call release() in a finally block even if acquire() throws."
```
**Flow:** route chain is `canView/canEdit/isOwner` (auth, sets `req.docAuth` via getOrSetDocAuth) → `validate(Checker)` (body schema) → `throttled(...)` → `_requireActiveDoc(...)` → handler. Inside throttle: read billing feature → acquire (increment parallel counter FIRST, then check parallel cap, then check/increment daily buckets → 429 on breach) → run inner handler → finally release.
**Invariant:** increment-before-check + finally-release means the parallel counter can never stick on a rejected request; a 429 still consumes+frees a slot transiently. Auth MUST run before throttle because dailyMax is read off `req.docAuth.cachedDoc`. Routes that must NOT load the ActiveDoc (`download`, `create-fork`, `recover`, `remove`, `flush`, `assign`, `replace`) use bare `throttled(...)` instead of `withDoc` — throttling and doc-loading are independent knobs.
**Probe:** `test/server/lib/DocApiUsageTracker.ts:11–67` ("parallel limits": allow-up-to-max :12, allow-after-release :22, per-doc independence :34; "daily limits": reject-when-exceeded :44, skip-when-undefined :58).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "DocApiUsageTracker throttle acquire release dailyMax", limit: 8,
  fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the increment-first/finally-release contract verbatim whenever a semaphore guards request handling. Adapt the billing-feature lookup to your plan store. Omit the Redis cross-worker daily counters only for single-process deployments (local LRU alone undercounts nothing — it just won't coordinate).
