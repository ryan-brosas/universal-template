<!-- capsule-v2 -->
# GET-only cache middleware — what is the one behavior of cacheHelpers and why does it exist at all?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What HTTP caching contract does getCacheMiddleware impose and what is the default TTL?

## GET-only cache middleware
**Path/Symbol:** `packages/nocodb/src/helpers/cacheHelpers.ts` — whole file 13L: `getCacheMiddleware(period: string | number = 2592000)` (:3–13).
**Signature:** `getCacheMiddleware(period?) → express RequestHandler` (async, calls next() always).
**Data Shape:** default 2592000 s = 30 days; header set ONLY for method === 'GET'.

### Decisive source
```ts
// :1–13 verbatim:
// return a middleware to set cache-control header
// default period is 30 days
export const getCacheMiddleware = (period: string | number = 2592000) => {
  return async (req, res, next) => {
    const { method } = req;
    // only cache GET requests
    if (method === 'GET') {
      // set cache-control header
      res.set('Cache-Control', `public, max-age=${period}`);
    }
    next();
  };
};
```

**Flow:** every request passes through; GETs get `Cache-Control: public, max-age=<period>`; everything else untouched.
**Invariant:** `public` (not private/no-store) is deliberate — these routes serve non-authenticated static-ish payloads where CDN/browser caching is wanted. Ports must keep the method gate or mutations would become cacheable. This is the ENTIRE module — its value is the default-TTL constant as policy, not machinery.
**Probe:** `grep -c "max-age=" packages/nocodb/src/helpers/cacheHelpers.ts` → `1`.
**Coverage caveat:** grep-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "getCacheMiddleware Cache-Control", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as-is including the 30-day default; adapt only if host serves authenticated payloads on the same routes.
