<!-- capsule-v2 -->
# ws-origin-verify-url-restore — How is a raw upgrade request verified before any websocket exists, and why does the verifier mutate and restore req.url?

**Source:** GristLabs grist-core Apache-2.0 `main@b83224bbe9c8`; Codebase Memory `grist-core`. **Question:** Before express middleware runs, how do you authenticate a websocket handshake that may carry doc-worker/version/org URL prefixes?

## verifyCommHttpRequest strip→verify→restore ladder
**Path/Symbol:** `app/server/lib/Comm.ts:verifyCommHttpRequest` (:279–307); wired as GristSocketServer verifyClient :263; `preserveOriginalUrl` option for proxying callers.
**Signature:** `export async function verifyCommHttpRequest(req: http.IncomingMessage, hosts?: Hosts, { preserveOriginalUrl = false } = {}): Promise<boolean>`.
**Data Shape:** input = RAW http.Server request (no express); may carry `/dw/<docWorkerId>/`, `/v/<versionTag>/`, `/o/<org>/` prefixes; output boolean; MUTATES req.url during check.

### Decisive source
```ts
const originalUrl = req.url;
try {
  if (hosts) {
    // Strip DocWorker ID and version tags so `addOrgInfo` can fetch the org it needs.
    req.url = parseFirstUrlPart("dw", req.url || "").path;
    req.url = parseFirstUrlPart("v", req.url).path;
    // This will strip `/o/ORG` from the URL, but organization *must* be forwarded.
    await hosts.addOrgInfo(req);
  }
  return trustOrigin(req);
} catch (err) {
  // Spammy/illegitimate traffic parses badly; no particular reason to log these.
  return false;
} finally {
  if (preserveOriginalUrl) {
    req.url = originalUrl;   // needed for transparent proxying use cases
  }
}
```

**Flow:** upgrade arrives → strip /dw/ then /v/ prefixes → addOrgInfo extracts + attaches org (strips /o/) → trustOrigin decides → exceptions ⇒ false SILENTLY (spam traffic, deliberately unlogged) → finally restores original URL only when the caller needs it (transparent proxying).
**Invariant:** verification happens BEFORE any websocket/express context exists, on the raw request — porters who wait for middleware have already leaked unauthenticated upgrades. The org is extracted but ALSO stripped: downstream connection handling must re-read org from the mutated request object (or restored original for proxies). Silent-false on parse errors is deliberate noise discipline, not error swallowing of legitimate traffic.
**Probe:** `test/server/Comm.ts:1073` "websocket auth" describe block — API key :1148, invalid-key terminate :1163, disabled user :1172, anonymous fallback :1182, boot key :1193, permit header :1220, identity-reuse matrix :1233+.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "verifyCommHttpRequest", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt strip-prefix→extract-org→trust-origin ordering with silent-false noise discipline. Adapt prefix vocabulary to your routing scheme. Omit Hosts plumbing if single-org; keep the restore-in-finally shape if anything downstream reads req.url.
