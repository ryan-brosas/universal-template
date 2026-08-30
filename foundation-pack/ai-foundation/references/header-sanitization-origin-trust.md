<!-- capsule-v2 -->
# Header sanitization + origin trust — which headers must be stripped before fetching untrusted URLs, and when may credentials ride along?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the exact blocklist for outbound untrusted requests, and how do isSameOrigin/credentialedOrigin/trustedOrigin divide the trust decisions?

## sanitizeRequestHeaders
**Path/Symbol:** `packages/provider-utils/src/sanitize-request-headers.ts:BLOCKED_REQUEST_HEADERS` (:15-45), `sanitizeRequestHeaders` (:47-53).
**Signature:** `sanitizeRequestHeaders(input: HeadersInit): Headers` — fresh Headers object, input never mutated.
**Data Shape:** Five blocked families: hop-by-hop transport (RFC 7230 §6.1: connection, keep-alive, te, trailer, transfer-encoding, upgrade); host routing (host); proxy/origin spoofing (forwarded, proxy-authorization, via, x-forwarded-for/host/proto, x-real-ip); cloud metadata (metadata, metadata-flavor, x-aws-ec2-metadata-token, x-metadata-token — GCP/AWS IMDSv1v2/Azure/Alibaba/DigitalOcean); session (cookie, set-cookie).

### Decisive source
```ts
// `Authorization` and other credential-bearing caller headers (e.g. `x-key`)
// are intentionally not listed — they're needed on the first hop of some
// provider polling calls. Instead, all caller headers except the user-agent are
// dropped on a cross-origin redirect (see `fetch-with-validated-redirects`).
export function sanitizeRequestHeaders(input: HeadersInit): Headers {
  const headers = new Headers(input);
  for (const name of BLOCKED_REQUEST_HEADERS) headers.delete(name);
  return headers;
}
```

**Flow:** applied once before the first hop of an untrusted fetch; cross-origin redirect credential dropping is a SEPARATE mechanism living in fetch-with-validated-redirects.
**Invariant:** Authorization/custom credential headers are deliberately NOT in this list (first-hop polling calls need them) — their protection is the per-hop cross-origin drop instead. Porting either half alone leaks: sanitize-without-drop sends `x-key` to redirect targets; drop-without-sanitize forwards cookies to the first hop.
**Probe:** pinned indirectly via get-from-api.test.ts header-snapshot tests (`:227`, `:41`) and fetch-with-validated-redirects flows; no dedicated unit file at this pin — recorded caveat.

## isSameOrigin + the two origin knobs
**Path/Symbol:** `packages/provider-utils/src/is-same-origin.ts:isSameOrigin` (:11-19, whole file).
**Signature:** `isSameOrigin(url: string, baseUrl: string): boolean`.
**Data Shape:** Compares full origins (scheme+host+port) via `new URL(...).origin`; ANY invalid absolute URL ⇒ false (fail-closed).

### Decisive source
```ts
// Returns false if either value is not a valid absolute URL (fail-closed).
try { return new URL(url).origin === new URL(baseUrl).origin; } catch { return false; }
```
**Flow:** consumed by getFromApi (`credentialedOrigin`: withhold ALL caller headers unless the target is same-origin with the configured base URL — UA suffix still applied) and by fetchWithValidatedRedirects (`trustedOrigin`: skip TARGET validation for hops same-origin with the developer-configured endpoint).
**Invariant:** The two knobs answer DIFFERENT questions — credentialedOrigin governs "may credentials ride", trustedOrigin governs "must this hop be SSRF-checked" — and BOTH must come from developer config, never from response data (get-from-api doc comments :46-54/:56-65). A response-supplied URL that happens to point back at the provider host still gets validated unless it matches the config-derived trustedOrigin exactly.
**Probe:** `packages/provider-utils/src/get-from-api.test.ts:248` (same-origin-as-trustedOrigin hops skip validation), `:266` (other origins still validated even with trustedOrigin set).

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"sanitizeRequestHeaders isSameOrigin credentialedOrigin trustedOrigin","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the five-family blocklist, the split responsibility (sanitize first hop / drop credentials on every cross-origin hop), and fail-closed origin comparison verbatim; adapt the metadata header family as new cloud providers appear; omit nothing from the blocklist — each entry maps to a real exfiltration or request-smuggling vector.
