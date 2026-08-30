<!-- capsule-v2 -->
# RouterExplorer.applyHostFilter — how is @Host() matching enforced, and where do captured host params come from?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** How does host filtering wrap a route handler, and how do `:param` fragments inside the host string become `req.hosts` values?

## applyHostFilter
**Path/Symbol:** `packages/core/router/router-explorer.ts:applyHostFilter` (:334-394).
**Signature:** `private applyHostFilter(host: string | RegExp | Array<string|RegExp>, handler): (req, res, next) => any`.
**Data Shape:** Compiles each string host via `pathToRegexp(host)` keeping its `keys`; RegExp hosts pass through as `{regexp, keys: []}`. Match captures land on a FRESH `req.hosts = {}` per request.

### Decisive source
```ts
return (req, res, next) => {
  (req as any).hosts = {};                          // reset EVERY request
  const hostname = httpAdapterRef.getRequestHostname(req) || '';
  for (const exp of hostRegExps) {
    const match = hostname.match(exp.regexp);
    if (match) {
      if (exp.keys.length > 0) {
        exp.keys.forEach((key, i) => (req.hosts[key.name] = match[i + 1]));
      } else if (exp.regexp && match.groups) {
        for (const groupName in match.groups) req.hosts[groupName] = match.groups[groupName];
      }
      return handler(req, res, next);
    }
  }
  if (!next) throw new InternalServerErrorException(unsupportedFilteringErrorMessage);
  return next();
};
```

**Flow:** compile-time: strings → pathToRegexp with named keys (TypeError on legacy syntax ⇒ loud migration log + rethrow); run-time: fresh hosts bag → adapter-normalized hostname → first matching expression wins → positional or group captures populate `req.hosts` → invoke handler; no match ⇒ pass to next middleware, or throw when there is none.
**Invariant:** (1) `@Host(':account.example.com')` values are consumed by `RouteParamsFactory.exchangeKeyForValue` case `HOST` (`data ? req.hosts[data] : req.hosts`) — route-params-factory.ts :27-30; without the per-request reset a previous request's captures could leak into a non-matching request. (2) The `!next` branch exists because non-middleware adapters call handlers directly — failing closed with 500 beats silently running a handler whose host didn't match. (3) First-match-wins across the host array mirrors the rest of Nest's resolution ladders.
**Probe:** `packages/core/test/router/router-explorer.spec.ts::applyVersionFilter` sibling coverage (:222); host param extraction pinned by `route-params-factory.spec.ts::exchangeKeyForValue` (host case).
**Coverage caveat:** applyHostFilter's own match/no-match matrix has no dedicated spec file — source-grounded; integration coverage via sample apps.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "RouterExplorer applyHostFilter req.hosts pathToRegexp", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the compile-once/filter-each-request wrapper for tenant-by-subdomain routing; adapt capture plumbing to your matcher's key shapes; omit the !next throw only in pure-middleware environments. Porting wrong: hoisting `req.hosts = {}` out of the closure (cross-request leakage), or reading host params from `req.params`.
