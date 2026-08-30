<!-- capsule-v2 -->
# RFC 9207 iss-on-redirect monkey patch — how does the SDK keep its `authorization_response_iss_parameter_supported: true` claim true without every provider appending `iss`?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** Where should the `iss` parameter be injected so providers need no changes — and when must the claim be retracted instead?

## Redirect-wrapper injection seam
**Path/Symbol:** `packages/server-legacy/src/auth/handlers/authorize.ts`: `withIssOnCallbackRedirect` (:210-233), wired at :186 (`issuer ? withIssOnCallbackRedirect(res, redirect_uri!, issuer) : res`); counterpart flag in `provider.ts` (:84-91) and metadata default in `router.ts` (:119-124).
**Signature:** `function withIssOnCallbackRedirect(res: Response, redirectUri: string, issuer: string): Response`; inner `appendIss(url: string): string`.
**Data Shape:** touches a redirect ONLY when `target.origin === cb.origin && target.pathname === cb.pathname && !target.searchParams.has('iss')`; preserves provider-set `iss`; handles all three Express redirect arities including the deprecated reversed `res.redirect(url, status)` form.

### Decisive source
```ts
// :225-231 wrap, don't rewrite the provider
const original = res.redirect.bind(res) as (...args: unknown[]) => void;
res.redirect = ((statusOrUrl: number | string, maybeUrl?: string | number): void => {
    if (typeof statusOrUrl === 'number') original(statusOrUrl, appendIss(String(maybeUrl)));
    // Express 4 still accepts the deprecated reversed form `res.redirect(url, status)`.
    else if (typeof maybeUrl === 'number') original(appendIss(statusOrUrl), maybeUrl);
    else original(appendIss(statusOrUrl));
}) as Response['redirect'];
```

**Flow:** handler passes the WRAPPED response to `provider.authorize`; any provider `res.redirect(...)` to the validated callback gets `iss=<issuer>` appended (RFC 9207 §2); redirects elsewhere — e.g. ProxyOAuthServerProvider bouncing to an upstream AS authorize URL (:128-146) — match neither origin nor pathname and pass through untouched. Error redirects are covered separately by `createErrorRedirect`, which sets `iss` explicitly (:248-251 "the iss parameter is required on error responses too"). The proxy provider sets `authorizationResponseIssParameterSupported = false` because the UPSTREAM issues the real callback; advertising `true` there would make RFC 9207 clients reject callbacks that omit `iss`.

**Invariant:** the metadata claim and the enforcement live together — either you append `iss` on every callback redirect (SDK default) or you advertise `false`; claiming support while delegating the callback to another issuer is the exact over-claim the flag exists to prevent. Origin+path matching means query-string-only differences still append, but a different path silently skips — porters who relax to origin-only will stamp foreign redirects.

**Probe (direct tests):** `packages/server-legacy/test/auth/handlers/authorize.test.ts` :410 "appends iss to the provider's success redirect and supplies issuer to provider.authorize()"; :428 'leaves redirects to non-callback targets untouched'; router.test.ts :226 derives the metadata flag from the provider; proxyProvider.test.ts pins upstream-redirect passthrough.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "withIssOnCallbackRedirect res redirect append iss", limit: 2 });
// → withIssOnCallbackRedirect Function 210-233 rank #1
```

## Verdict
Adopt response-wrapping as the single injection point and the claim-vs-enforcement coupling; adapt the wrapper to your framework's redirect API surface; omit the deprecated reversed-form shim if your framework never supported it.
