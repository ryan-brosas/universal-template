<!-- capsule-v2 -->
# Origin allowlist validation — how do you deny cross-origin browser attacks without breaking non-browser MCP clients?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** Browsers send `Origin` on state-changing cross-site requests; non-browser clients never do — what exact pass/deny rule set defends an MCP server (DNS rebinding / CSRF companion) without false-blocking CLI agents?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/middleware/originValidation.ts`: `validateOriginHeader` (:38-60), type `OriginValidationResult` (:18-26), `localhostAllowedOrigins` (:66-68), `originValidationResponse` (:80-98). Graph qn `typescript-sdk.packages.server.src.server.middleware.originValidation.validateOriginHeader`.
**Signature:** `validateOriginHeader(originHeader: string|null|undefined, allowedOriginHostnames: string[]): OriginValidationResult` where result = `{ok:true; origin?; hostname?} | {ok:false; errorCode:'invalid_origin_header'|'invalid_origin'; message; originHeader?; hostname?}`.
**Data Shape:** Allowlist = hostnames ONLY (no scheme, no port — port/scheme agnostic matching); IPv6 entries carry brackets (`'[::1]'`). `originValidationResponse` returns `undefined` to proceed or a ready `403 Response` with body `{jsonrpc:'2.0', error:{code:-32000, message}, id:null}`.

### Decisive source
```ts
if (originHeader === null || originHeader === undefined || originHeader === '') {
    return { ok: true };  // absent ⇒ pass: only browser requests carry Origin
}
let hostname: string;
try { hostname = new URL(originHeader).hostname; }
catch { return { ok: false, errorCode: 'invalid_origin_header', … }; }   // deny-on-failure
if (hostname === '') {
    // Opaque origins ("null") and other non-hierarchical values parse without a
    // hostname; they can never be allowlisted.
    return { ok: false, errorCode: 'invalid_origin_header', … };
}
if (!allowedOriginHostnames.includes(hostname)) {
    return { ok: false, errorCode: 'invalid_origin', … };
}
return { ok: true, origin: originHeader, hostname };
```

**Flow:** absent/empty ⇒ pass → parse as URL ⇒ unparseable ('not a url', 'evil.example.com', 'about:blank') ⇒ DENY (`invalid_origin_header`) → parsed-but-hostname-empty (the literal `'null'` opaque origin!) ⇒ DENY (`invalid_origin_header`) → hostname not in allowlist ⇒ DENY (`invalid_origin`) — including lookalike subdomains (`localhost.evil.example.com` fails the exact-match includes) → else pass carrying parsed hostname. The Response wrapper turns every failure into a uniform `403` JSON-RPC error so callers just `if (rejected) return rejected;`.

**Invariant:** DENY-ON-FAILURE for any present value: there is no code path where a present-but-unparseable Origin passes — the two distinct error codes separate "header itself malformed/opaque" from "well-formed but not allowed", letting operators tune allowlists without weakening the parser. Exact hostname equality (no suffix/wildcard matching) is what kills subdomain lookalikes. Missing-Origin pass is safe precisely because Host-header validation (sibling capsule) independently blocks DNS-rebinding hosts.

**Probe:** `packages/server/test/server/originValidation.test.ts` — :10 absent/null/empty pass, :16 port/scheme-agnostic allow incl. `[::1]:8080`, :23 non-allowlisted reject, :32 subdomain-lookalike reject, :36 deny-on-failure loop over `['null','not a url','evil.example.com','about:blank']`, :56 403 shape with `-32000`. Node adapter guard mirror: `packages/middleware/node/test/validation.test.ts` :48 (403 + request-reported-handled).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "validateOriginHeader originValidationResponse localhostAllowedOrigins", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt absent-pass/present-deny split, two-code taxonomy, empty-hostname (opaque null) rejection, and exact-match hostname allowlisting. Adapt error-message wording and the -32000 body if your host uses a different error envelope. Omit nothing; pair with host-header validation — Origin checks alone are incomplete DNS-rebinding defense.
