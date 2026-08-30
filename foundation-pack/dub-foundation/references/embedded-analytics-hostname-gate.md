<!-- capsule-v2 -->
# Embedded analytics hostname gate — which origins may RECORD events

**Source:** dub AGPL-3.0-or-later `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `dub`. **Question:** Where does dub enforce that only approved hosts can record track events, and what exactly counts as a match?

## verifyAnalyticsAllowedHostnames on the ingest routes
**Path/Symbol:** `apps/web/lib/analytics/verify-analytics-allowed-hostnames.ts:getHostnameFromRequest` (:1-11) + `verifyAnalyticsAllowedHostnames` (:13-59). Inbound callers (trace_path): `app/(ee)/api/track/{visit,click,lead/client,sale/client}/route.ts` — an INGEST boundary, not a query boundary.
**Signature:** `verifyAnalyticsAllowedHostnames({ allowedHostnames: string[], req: Request }): boolean`.
**Data Shape:** `allowedHostnames` supports exact hostnames and `*.domain` wildcards; hostname derived from referer||origin header, www.-stripped.

### Decisive source
```ts
// If no allowed hostnames are set, allow the request
if (!allowedHostnames || allowedHostnames.length === 0) {
  return true;
}

const hostname = getHostnameFromRequest(req);
if (!hostname) {
  ...
  return false;
}

// Check for exact matches first (including root domain)
if (allowedHostnames.includes(hostname)) {
  return true;
}

const wildcardMatches = allowedHostnames
  .filter((domain) => domain.startsWith("*."))
  .map((domain) => domain.slice(2));

for (const domain of wildcardMatches) {
  // Allow only proper subdomains: ensure hostname ends with ".domain.com"
  if (hostname.endsWith(`.\${domain}`)) {
    return true;
  }
}
...
return false;
```
(verify-analytics-allowed-hostnames.ts :20-49 condensed)

**Flow:** EMPTY allowlist ⇒ allow-all (restriction is opt-in per program/workspace) → unparseable or absent referer/origin ⇒ DENY (fail-closed for configured programs) → exact-match pass → wildcard pass requiring a proper-subdomain suffix → anything else denied with a log line.
**Invariant:** a `*.domain` entry does NOT cover the apex `domain` itself (apex must be listed exactly); the gate protects event RECORDING for embedded/public dashboards — query APIs are authorized separately.

**Probe:** executed: `grep -n 'allowedHostnames.includes(hostname)' ...` → :35; `grep -n 'startsWith("\\*.")' ...` → :41; `grep -n 'endsWith' ...` → :46; caller sweep `grep -rln verifyAnalyticsAllowedHostnames apps/web/app` → the four track route files above. No dedicated unit test file exists for this module (recorded caveat); behavior confirmed by whole-file read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", name_pattern: "^(verifyAnalyticsAllowedHostnames|getHostnameFromRequest)$", limit: 5 });
```

## Verdict
Adopt opt-in restriction with fail-closed deny once configured, and the proper-subdomain-only wildcard rule. Adapt header sources (referer/origin) to your embed surface. Omit the console.log telemetry.
