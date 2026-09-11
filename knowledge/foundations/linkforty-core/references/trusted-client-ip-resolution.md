<!-- capsule-v2 -->
# Trusted client-IP resolution — authoritative proxy header opt-in with spoofing precondition

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** When may a server believe an IP-bearing request header, and what must be true before it does?

## getClientIp header-first ladder
**Path/Symbol:** `src/lib/client-ip.ts:getClientIp` (:23-40); consumed by targeting, click ingestion, fingerprinting (redirect.ts/sdk.ts call sites).
**Signature:** `function getClientIp(request: FastifyRequest): string`.
**Data Shape:** Reads env `TRUSTED_CLIENT_IP_HEADER` (lowercased/trimmed name, e.g. `cf-connecting-ip`, `true-client-ip`); handles array-valued headers and comma-separated lists (first entry wins); unwraps `::ffff:` IPv4-mapped IPv6; falls back `request.ip ?? request.raw.socket?.remoteAddress`; returns `''` when nothing is available.

### Decisive source
```ts
// client-ip.ts:17-22 — the precondition a porter MUST carry:
// IMPORTANT: only enable this when the origin is reachable
// ONLY through that proxy — otherwise a direct client could spoof the header.
// When unset, behavior is unchanged (uses `request.ip`).
const headerName = process.env.TRUSTED_CLIENT_IP_HEADER?.toLowerCase().trim();
if (headerName) {
  const raw = request.headers[headerName];
  const value = Array.isArray(raw) ? raw[0] : raw;
  if (value && typeof value === 'string') {
    const first = value.split(',')[0]?.trim();
    if (first) return normalizeIp(first);
  }
}
```

**Flow:** Behind a CDN that terminates the connection (Cloudflare), Fastify's left-most-XFF-derived `request.ip` can be an edge/NAT hop rather than the client; the deployment opts into one authoritative header; every consumer (geo targeting, bot-free analytics counts, fingerprint ip-factor) shares this single resolver — doc comment says "Use this everywhere client IP is needed".
**Invariant:** Header trust requires network-level origin lockdown (origin reachable ONLY through the trusted proxy); default-off preserves stock behavior; one choke point per codebase so targeting/attribution/fingerprinting cannot disagree about the client.
**Probe:** `bash -c "grep -cF 'TRUSTED_CLIENT_IP_HEADER' src/lib/client-ip.ts"` → 2 (:17 doc comment + :24 code — count LINES not occurrences); direct tests `src/lib/client-ip.test.ts`: describe('getClientIp with TRUSTED_CLIENT_IP_HEADER') incl. "takes the first entry of a comma-separated header value", "ignores the header when the env var is unset" + trustProxy describe block.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "getClientIp trusted header cf-connecting-ip", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-choke-point IP resolver with documented spoofing precondition; adapt header names per your CDN; omit the header tier when you have no terminating proxy — but keep ::ffff: unwrapping regardless.
