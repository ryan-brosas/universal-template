<!-- capsule-v2 -->
# SSRF download guard — how do you fetch model-supplied URLs without letting a redirect or DNS rebinding reach the internal network?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What must be validated on EVERY hop of a redirect chain, and why does native `redirect: 'follow'` defeat the whole guard?

## fetchWithValidatedRedirects
**Path/Symbol:** `packages/provider-utils/src/fetch-with-validated-redirects.ts:fetchWithValidatedRedirects` (:61-155); helpers `validateDownloadUrl`/`validateDownloadAddress` in `validate-download-url.ts` (:13-87/:89-111).
**Signature:** `fetchWithValidatedRedirects({url, headers?, abortSignal?, maxRedirects? = 10, fetch?, trustedOrigin?}): Promise<Response>`; `REDIRECT_STATUS_CODES = {301,302,303,307,308}` (300/304 are NOT redirects even with a Location header, :12-15).
**Data Shape:** Returns the final non-redirect Response; throws `DownloadError` on unsafe hop / limit exceeded / unvalidatable opaque redirect.

### Decisive source
```ts
for (let redirectCount = 0; redirectCount <= maxRedirects; redirectCount++) {
  const isTrustedHop = trustedOrigin !== undefined && isSameOrigin(currentUrl, trustedOrigin);
  if (!isTrustedHop) validateDownloadUrl(currentUrl);      // validate BEFORE requesting
  const fetch = customFetch ?? (isTrustedHop ? globalThis.fetch : await getDefaultDownloadFetch());
  const response = await fetch(currentUrl, perHopInit('manual'));   // manual = we see every hop
  if (response.type === 'opaqueredirect') {
    if (!isBrowserRuntime()) throw new DownloadError({ url, message:
      `Redirect from ${currentUrl} could not be validated and was blocked` }); // fail closed
    return await fetch(currentUrl, perHopInit('follow'));  // browser: CORS already constrains
  }
  const location = response.headers.get('location');
  if (REDIRECT_STATUS_CODES.has(response.status) && location) {
    await cancelResponseBody(response);                    // unconsumed 3xx body leaks the socket
    const nextUrl = new URL(location, currentUrl).toString();
    if (currentHeaders !== undefined && !isSameOrigin(nextUrl, currentUrl)) {
      // drop ALL caller headers except user-agent (fetch spec only strips Authorization;
      // server-side there is no CORS, so custom headers like `x-key` must be dropped too)
      currentHeaders = new Headers(userAgent == null ? undefined : { 'user-agent': userAgent });
    }
    currentUrl = nextUrl; continue;
  }
  return response;
}
throw new DownloadError({ url, message: `Too many redirects (max ${maxRedirects})` });
```

**Flow:** sanitize headers once → per hop: trusted-origin check → target validation → fetch with `redirect:'manual'` → opaque-redirect branch (browser follows natively, other runtimes fail closed) → redirect branch (cancel old body, resolve relative Location, drop credentials cross-origin, loop) → final response.
**Invariant:** Validation happens BEFORE each request — relying on `redirect:'follow'` issues the request to the target before you ever see its URL, defeating the guard (source comment :20-24). Header snapshots are taken PER HOP (`new Headers(currentHeaders)` in `perHopInit`, comment :88-90) because an injected fetch may defer reading them, and hops after a credential drop would otherwise share one mutable instance.
**Probe:** `packages/provider-utils/src/get-from-api.test.ts:53` (safe redirect followed + hop validated), `:76` (private-address redirect rejected without request), `:88` (redirect body cancelled before next hop), `:186` (opaque redirect fails closed outside browser), `:227` (per-hop independent header snapshots), `:248/:266` (trustedOrigin skip/scoping).

## Address blocklist — string checks plus connect-time DNS pinning
**Path/Symbol:** `packages/provider-utils/src/validate-download-url.ts:isPrivateIPv4` (:124-162), `parseIPv6` (:164-208), `isPrivateIPv6` (:210-272), `validateDownloadAddress` (:89-111).
**Signature:** `validateDownloadUrl(url): void` throws on non-http(s)/data scheme, empty hostname, `localhost*`/`*.local` (trailing-dot FQDN stripped first, :39), private IPv4, private IPv6.
**Data Shape:** IPv4 ranges blocked: `0/8, 10/8, 100.64/10 (CGNAT), 127/8, 169.254/16, 172.16/12, 192.0.0/24, 192.0.2/24, 192.168/16, 198.18/15, 198.51.100/24, 203.0.113/24, ≥224 (multicast+reserved)`.

### Decisive source
```ts
// Addresses that embed an IPv4 address in their last 32 bits. For these we
// extract the embedded IPv4 and reuse the IPv4 private-range checks, so that
// e.g. ::ffff:127.0.0.1 or 64:ff9b::169.254.169.254 are blocked.
const embedsIPv4 =
  topZero(6) ||                                            // ::/96 IPv4-compatible
  (topZero(5) && groups[5] === 0xffff) ||                  // ::ffff:0:0/96 mapped
  (topZero(4) && groups[4] === 0xffff && groups[5] === 0) || // translated form
  (groups[0] === 0x0064 && groups[1] === 0xff9b /* … NAT64 */) ;
if (embedsIPv4) { const [a,b,c,d] = /* last 32 bits */; return isPrivateIPv4(`${a}.${b}.${c}.${d}`); }
```
**Flow:** literal checks at URL level (`validateDownloadUrl`) → Node's default download fetch installs a validating DNS lookup hook calling `validateDownloadAddress` per resolved address (hostname-to-private-IP and DNS-rebinding bypass closed at CONNECT time; injected fetches must supply equivalent validation — header comment :52-56).
**Invariant:** Unparseable IPv6 fails CLOSED (`groups === null ⇒ true`). `data:` URLs are allowed through untouched (inline content, no fetch). String-level blocking alone is NOT sufficient on Node — the DNS pinning hook is what stops rebinding.
**Probe:** `packages/provider-utils/src/read-response-with-size-limit.test.ts:62/:83` (early Content-Length rejection + socket release), `:160` (lying Content-Length still caught by streamed count).

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"fetchWithValidatedRedirects validateDownloadUrl isPrivateIPv6 opaqueredirect","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt validate-before-request-per-hop, manual redirects, cross-origin credential dropping beyond the spec's Authorization-only rule, and the embedded-IPv4 reuse of v4 range checks; adapt the trustedOrigin escape hatch only if you have config-derived endpoints (never derive it from responses); omit browser-runtime special casing if your runtime has no CORS concept. Coverage caveat: the blocklist internals are pinned indirectly via get-from-api integration tests; no dedicated unit file for validate-download-url at this pin.
