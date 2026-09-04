<!-- capsule-v2 -->
# Fetch middleware composition — how do OAuth retry and logging compose over fetch without entangling transports?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** What is the shape of a composable fetch-middleware layer for MCP-adjacent HTTP, and where does 401 re-auth belong in it?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/middleware.ts` (whole, 319L): `Middleware = (next: FetchLike) => FetchLike` (:12), `withOAuth(provider, baseUrl?)` (:38-156), `withLogging(options?)` (:158), `applyMiddlewares(...mws)` (:249-259), `createMiddleware(handler)` (:317-319).
**Signature:** `applyMiddlewares = (...middleware: Middleware[]): Middleware => next => { let h = next; for (const mw of middleware) handler = mw(handler); return handler; }`.
**Data Shape:** Each middleware wraps the NEXT handler; composition is left-associative so `applyMiddlewares(a, b)(fetch)` runs a's pre-code first. 401 handling reads `WWW-Authenticate` params (`resourceMetadataUrl`, `scope`) then reruns `auth()` and retries ONCE via the inner chain.

### Decisive source
```ts
let response = await makeRequest();
// Handle 401 responses by attempting re-authentication
if (response.status === 401) {
    const { resourceMetadataUrl, scope } = extractWWWAuthenticateParams(response);
    const serverUrl = baseUrl || new URL(input instanceof URL ? input.href : input).origin;
    const result = await auth(provider, { serverUrl, resourceMetadataUrl, scope, fetchFn: next });
    …
}
```

**Flow:** request → token attach if provider holds tokens → send → on 401: parse challenge → run the SDK auth flow with the INNER handler as fetchFn → retry original request with fresh tokens → surface OAuth error taxonomy otherwise. Logging wraps status-level filtering around any link in the chain.

**Invariant:** Transports (SSE/StreamableHTTP) already have built-in OAuth — this wrapper is for GENERAL-purpose fetches; double-wrapping double-prompts. `baseUrl` must match the transport's URL when discovery paths differ from API paths (subdomain/cross-domain default-origin inference breaks those cases).

**Probe:** `packages/client/test/client/middleware.test.ts` (composition order, 401 retry ladder, logging filters).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "withOAuth applyMiddlewares createMiddleware", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt the `(next)=>FetchLike` closure-chain shape for transport-agnostic HTTP middleware; adapt the auth ladder to your provider; omit logging unless wanted.
