<!-- capsule-v2 -->
# Host header allowlist — how do you block DNS rebinding with a three-line parse that still handles IPv6 and ports?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** Every HTTP/1.1 request carries an attacker-controllable `Host` header — what is the minimal correct validation that stops rebinding attacks without breaking `localhost:3000`-style development traffic?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/middleware/hostHeaderValidation.ts`: `validateHostHeader` (:17-35), type `HostHeaderValidationResult` (:1-9), `localhostAllowedHostnames` (:40-42), `hostHeaderValidationResponse` (:51-69). Graph qn `typescript-sdk.packages.server.src.server.middleware.hostHeaderValidation.validateHostHeader`.
**Signature:** `validateHostHeader(hostHeader: string|null|undefined, allowedHostnames: string[]): HostHeaderValidationResult` where result = `{ok:true; hostname} | {ok:false; errorCode:'missing_host'|'invalid_host_header'|'invalid_host'; message; hostHeader?; hostname?}`.
**Data Shape:** Input header may carry a port (`localhost:3000`) or IPv6 brackets (`[::1]:3000`); allowlist items are bare hostnames (IPv6 WITH brackets). Response helper returns `undefined` to proceed or a ready `403` whose body is `{jsonrpc:'2.0', error:{code:-32000, message}, id:null}`.

### Decisive source
```ts
if (!hostHeader) { return { ok: false, errorCode: 'missing_host', … }; }
// Use URL API to parse hostname (handles IPv4, IPv6, and regular hostnames)
let hostname: string;
try { hostname = new URL(`http://${hostHeader}`).hostname; }
catch { return { ok: false, errorCode: 'invalid_host_header', … }; }
if (!allowedHostnames.includes(hostname)) {
    return { ok: false, errorCode: 'invalid_host', … };
}
return { ok: true, hostname };
```

**Flow:** missing ⇒ deny (`missing_host`) → prefix `http://` and parse via the URL API so ports strip and IPv6 brackets normalize — `new URL('http://' + '[::1]:3000').hostname === '[::1]'` → exact-match against the hostname-only allowlist → pass carrying the parsed hostname; any failure becomes a uniform `403` JSON-RPC error via the wrapper.

**Invariant:** Unlike Origin validation, MISSING is a denial here: HTTP/1.1 requires `Host`, so absence means a non-conformant client (and DNS-rebinding defense must fail closed). Port-agnosticism comes free from `URL.hostname` — never compare the raw header, or `localhost:3000 ≠ localhost` breaks dev servers while attacker-controlled ports sneak through naive suffix matches. Same allowlist convention as Origin validation (hostnames only, bracketed IPv6) lets one constant feed both checks.

**Probe:** No dedicated upstream suite at this pin for the core file (coverage caveat). Behavior is pinned indirectly through adapter guards exercising the same helpers: `packages/middleware/node/test/validation.test.ts` :23 (disallowed Host ⇒ 403 + handled), :38 (allowed Host port-agnostic), plus express/hono/fastify suites (`originValidation.test.ts`, `express.test.ts`). The 403 body shape mirrors `originValidationResponse`, which IS directly tested (:56).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "validateHostHeader hostHeaderValidationResponse localhostAllowedHostnames", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt missing-denies + URL-API hostname extraction + exact-match allowlist as the whole algorithm — it is deliberately tiny. Adapt the -32000 envelope to your error convention. Omit regex-based host parsing (the trap this design avoids).
