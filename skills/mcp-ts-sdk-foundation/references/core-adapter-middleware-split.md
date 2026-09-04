<!-- capsule-v2 -->
# Core/adapter middleware split — how do you write HTTP middleware once and port it to Express/Hono/Fastify/Node without forking the logic?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** Four framework packages ship the "same" auth/validation middleware — what is the layering contract that keeps the decision logic single-sourced and only the shell per-framework?

## Connected graph-selected seam
**Path/Symbol:** `packages/middleware/express/src/auth/bearerAuth.ts`: adapter `requireBearerAuth` (:26-47) over core `verifyBearerToken`/`bearerAuthChallengeResponse` (`packages/server/src/server/middleware/bearerAuth.ts` :94-124/:136-163). Same pattern: `packages/middleware/{express,hono,fastify,node}/src/{auth,middleware}/…`. Graph qn `typescript-sdk.packages.middleware.express.src.auth.bearerAuth.requireBearerAuth`.
**Signature:** Adapter: `requireBearerAuth(options): RequestHandler` — same options type as core (`BearerAuthMiddlewareOptions = BearerAuthOptions`, type-aliased not duplicated).
**Data Shape:** Core exposes three altitudes of the SAME logic: (1) pure verify (`verifyBearerToken(header, options) → AuthInfo`, throws OAuthError), (2) error→HTTP mapper (`bearerAuthChallengeResponse(error, options) → Response`), (3) pre-composed gates (`requireBearerAuth` fetch-gate returning `Promise<AuthInfo | Response>`).

### Decisive source
```ts
export function requireBearerAuth(options: BearerAuthMiddlewareOptions): RequestHandler {
    // Destructure at creation so a plain-JS caller passing undefined or
    // malformed options crashes at startup, not on the first request.
    const { verifier, requiredScopes = [], resourceMetadataUrl } = options;
    const resolved = { verifier, requiredScopes, resourceMetadataUrl };
    return async (req, res, next) => {
        try {
            req.auth = await verifyBearerToken(req.headers.authorization, resolved);
            next();
        } catch (error) {
            // The core Response supplies status and challenge; the body is
            // derived directly rather than parsed back out of the Response.
            const response = bearerAuthChallengeResponse(error, resolved);
            const challenge = response.headers.get('WWW-Authenticate');
            if (challenge !== null) { res.set('WWW-Authenticate', challenge); }
            const body = error instanceof OAuthError ? error : new OAuthError(OAuthErrorCode.ServerError, 'Internal Server Error');
            res.status(response.status).json(body.toResponseObject());
        }
    };
}
```

**Flow:** The adapter owns ONLY framework mechanics: read `req.headers.authorization` (Node keeps first of duplicates — no comma-join problem like Fetch), attach result to `req.auth` (the transport later surfaces it to handlers as `ctx.http.authInfo`), call `next()`. On failure it REUSES the core's Response as a header/status oracle but rebuilds the JSON body from the original OAuthError instead of `response.json()` — because an express `res.json()` cannot consume a web-standard Response body without async extraction. Result-attachment point (`req.auth`) is the adapter's side of the contract with the transport.

**Invariant:** Zero auth DECISIONS live in adapters — every ladder step, status mapping, scope rule, and sanitization rule is in `@modelcontextprotocol/server`; an adapter that re-implements any check has forked the security logic. Options destructured at CREATION in both layers (startup-crash parity). Status/challenge always come from the core mapper even when the body doesn't — the two can never disagree. Framework ports (hono/fastify/node `originValidation`/`hostHeaderValidation`) wrap the same core helpers with their own guard signatures (e.g. node returns boolean handled + writes 403 via `res.writeHead`).

**Probe:** `packages/middleware/express/test/auth/resourceServer.test.ts` :36 (attaches req.auth + next), :55 (401 + WWW-Authenticate incl resource_metadata), :103 (403 with scope in challenge), :121/:133 (500 no-challenge), :145 (400 other codes); `packages/middleware/node/test/validation.test.ts` :23/:38/:48 (guard 403s through node primitives). Core suite pins the identical statuses — proving both shells answer identically.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "requireBearerAuth express middleware bearerAuth", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt the three-altitude split (pure verify / error-mapper / composed gate) plus creation-time option resolution for ANY multi-framework middleware; adapt the attachment convention (req.auth vs ctx vs return union) per host; omit per-framework re-implementations of decision logic entirely.
