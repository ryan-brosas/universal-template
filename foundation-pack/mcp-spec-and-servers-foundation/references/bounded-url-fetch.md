<!-- capsule-v2 -->
# Bounded URL fetch for tool inputs — how does a tool fetch attacker-supplied URLs without OOM, hang, or SSRF into disallowed hosts?

**Source:** modelcontextprotocol/servers MIT `main@76d64c82`; Codebase Memory `servers`. **Question:** What is the minimal defense ladder a tool must run before and WHILE fetching a user-provided URL, given that Content-Length is untrusted?

## Protocol allowlist → domain allowlist → AbortController timeout → stream-and-count bytes
**Path/Symbol:** `src/everything/tools/gzip-file-as-resource.ts` (whole file, 248L: env-configured limits :11–24; `validateDataURI` :135–168; `fetchSafely` :180–248). Tool then gzips the buffer and publishes it as a session resource via `getSessionResourceURI` + `registerSessionResource` (:91–106) returning either an inline `resource` content block or a `resource_link` per the `outputType` arg (:109–124).

**Signature:** `validateDataURI(dataUri: string) → URL` (throws on unsupported protocol / disallowed domain); `fetchSafely(url: URL, { maxBytes, timeoutMillis }) → Promise<ArrayBuffer>`. Limits from env with safe defaults: `GZIP_MAX_FETCH_SIZE` = 10 MB, `GZIP_MAX_FETCH_TIME_MILLIS` = 30 000, `GZIP_ALLOWED_DOMAINS` = comma list, empty = all allowed.

**Data Shape:** streaming read accumulates `{ done, value }` chunks; `totalSize += value.length` is checked AFTER every chunk against `maxBytes`; chunks spliced into one Uint8Array at the end.

### Decisive source
```ts
// gzip-file-as-resource.ts:200-231 — don't trust Content-Length; count actual bytes
// Note: we can't trust the Content-Length header: a malicious or clumsy server could
// return much more data than advertised. We check it here for early bail-out, but we
// still need to monitor actual bytes read below.
const contentLengthHeader = response.headers.get("content-length");
if (contentLengthHeader != null) {
  const contentLength = parseInt(contentLengthHeader, 10);
  if (contentLength > maxBytes) { throw new Error(`Content-Length for ${url} exceeds max of ${maxBytes}: ${contentLength}`); }
}
const reader = response.body.getReader();
...
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  totalSize += value.length;
  if (totalSize > maxBytes) {
    reader.cancel();
    throw new Error(`Response from ${url} exceeds ${maxBytes} bytes`);
  }
  chunks.push(value);
}
```
Protocol gate (:139–147): only `http:`, `https:`, `data:` pass. Domain gate (:149–159): when configured, exact match OR `endsWith("." + allowed)` subdomain match — `notevil.com` does NOT match `evil.com`.

**Flow:** parse URL (throws on garbage) → protocol allowlist → domain allowlist (if non-empty) → `fetch` with AbortController timer (`setTimeout(() => controller.abort(...), timeoutMillis)`) → cheap Content-Length early bail → chunked read with running total, cancel+throw past cap → assemble buffer → `gzipSync` → session-resource registration (`registerSessionResource(server, resource, "blob", base64)`) → emit chosen shape; unknown `outputType` throws. `clearTimeout` in `finally` (:245–247).

**Invariants:**
1. **Content-Length is advisory; the byte counter is the enforcement** — trusting the header lets a lying server stream unbounded memory.
2. **Timeout must arm BEFORE fetch and clear in finally** — otherwise a hung connection leaks both time and the abort controller.
3. Subdomain matching must anchor on `.domain` suffixes — naive `includes()` would let `evildomain.com` pass an `domain.com` allowlist.
4. Oversize responses are REJECTED (throw), not truncated — silent truncation corrupts downstream binary processing (here: gzip).

**Probe:** `src/everything/__tests__/tools.test.ts:1142–1230` — compresses a data URI and asserts resource-link shape, asserts full-resource output path, and pins protocol rejection ("should reject unsupported URL protocols"). Domain-allowlist branch has no direct test — coverage caveat recorded (deterministic probe = source :149–159).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "fetchSafely maxBytes AbortController reader cancel validateDataURI allowed domains", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the four-gate ladder (protocol → domain → deadline → counted stream) for ANY tool that fetches client-supplied URLs; adapt limit values and domain policy to your product; omit the gzip/session-resource payload handling (covered by `session-resource-reregistration.md`). Complements `filesystem-sandbox.md` (that guards the local FS; this guards outbound fetch).
