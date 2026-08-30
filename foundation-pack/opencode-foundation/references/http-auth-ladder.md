<!-- capsule-v2 -->
# Loopback HTTP auth ladder — how do you authenticate both fetch and EventSource clients against one shared password, and why must you avoid framework security-alternative middleware?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** How does a local dev server accept Basic auth from normal HTTP clients AND header-less SSE/EventSource clients, while preserving handler error semantics?

## Query-first credential resolution, three middleware tiers
**Path/Symbol:** `packages/opencode/src/server/routes/instance/httpapi/middleware/authorization.ts` (`AUTH_TOKEN_QUERY` :12, `credentialFromURL` :77-83, `validateCredential` :40-55, router variant :101-116, pty variant :134-150) + `packages/opencode/src/server/auth.ts` (`required` :24-26, `authorized` :28-34).
**Signature:** `required(config) → boolean`; `authorized({username, password:Redacted}, config) → boolean`; `Authorization extends HttpApiMiddleware.Service` (error: `UnauthorizedNoContent`).
**Data Shape:** credentials = base64 `user:pass` split at the FIRST ":"; sources in priority order: `?auth_token=` query param → `Authorization: Basic` header → empty. Config: `OPENCODE_SERVER_PASSWORD` (optional; unset or "" disables auth), `OPENCODE_SERVER_USERNAME` (default "opencode").

### Decisive source
```ts
// authorization.ts:16-18 — the design decision, verbatim:
// Avoid HttpApiSecurity alternatives here: Effect security middleware wraps the
// full handler, so a downstream failure can make the next auth alternative run
// and remap an authorized NotFound into Unauthorized.
// :78-81 — query param wins because EventSource cannot set headers:
const token = url.searchParams.get(AUTH_TOKEN_QUERY)
if (token) return decodeCredential(token)
const match = /^Basic\s+(.+)$/i.exec(request.headers.authorization ?? "")
```

**Flow:** typed-API tier wraps handler effects: no-op when auth not required; on failure appends `WWW-Authenticate: Basic realm="Secure Area"` via pre-response handler and raises Unauthorized (:48-51). Raw-router tier (UI catch-all + /doc) returns an empty 401 response directly and bypasses `isPublicUIPath`. PTY-connect tier bypasses entirely when the URL carries a valid connect ticket (`hasPtyConnectTicketURL`). v2 server tier re-exports the shared implementation from `@opencode-ai/server/middleware/authorization`.
**Invariant:** Auth is disabled wholesale when password is unset/empty (`required()`). Handler errors are never remapped by auth machinery — a 404 behind valid credentials stays 404 (pinned twice in tests). Query credentials take precedence over header credentials. Honest caveat: comparison is plain string equality, NOT constant-time — acceptable local-dev posture; harden with timingSafeEqual when porting to multi-user hosts without changing the ladder shape.
**Probe:** `packages/opencode/test/server/httpapi-authorization.test.ts` — ":88 requires configured password" (401+WWW-Authenticate vs 200), ":119 accepts auth token query credentials", ":127 prefers query over basic", ":137/:148 preserve handler errors" (404 stays 404 through both credential paths), ":156 rejects malformed auth token", ":164 bodyful v2 unauthorized `{_tag:"UnauthorizedError"}`"; source pin:
```bash
grep -n 'remap an authorized NotFound into Unauthorized' packages/opencode/src/server/routes/instance/httpapi/middleware/authorization.ts
```
expect 1 hit at :18.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "auth_token basic credentials unauthorized www-authenticate middleware", limit: 8 });
```

## Verdict
Adopt query-param-first credentials for header-less clients, config-absence-disables-auth, per-tier variants sharing one validator, and the no-security-alternatives rationale; adapt the ticket mechanism and username defaults; omit opencode's specific env names.
