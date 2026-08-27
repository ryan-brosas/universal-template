<!-- capsule-v2 -->
# Header default fallback and data-URL text decode — which tiny helpers carry load-bearing one-way semantics?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** Why does header merging prefer caller values over defaults, and what are the failure modes of the legacy data-URL text decoder?

## prepareHeaders
**Path/Symbol:** `packages/ai/src/util/prepare-headers.ts:prepareHeaders` (:1-14); companion `packages/ai/src/util/data-url.ts:getTextFromDataUrl` (:4-17).
**Signature:** `prepareHeaders(headers: HeadersInit | undefined, defaultHeaders: Record<string, string>): Headers`; `getTextFromDataUrl(dataUrl: string): string`.
**Data Shape:** Returns a NEW `Headers` instance; defaults fill only ABSENT keys — a caller-supplied value (even a weird one) is never overwritten. The data-URL decoder returns decoded text or throws plain `Error`.

### Decisive source
```ts
const responseHeaders = new Headers(headers ?? {});
for (const [key, value] of Object.entries(defaultHeaders)) {
  if (!responseHeaders.has(key)) {     // has() check = caller wins, default only fills gaps
    responseHeaders.set(key, value);
  }
}
```
```ts
const [header, base64Content] = dataUrl.split(',');
const mediaType = header.split(';')[0].split(':')[1];
if (mediaType == null || base64Content == null) throw new Error('Invalid data URL format');
try { return window.atob(base64Content); } catch { throw new Error('Error decoding data URL'); }
```

**Flow:** merge direction is DEFAULTS-FILL-GAPS (`has()` guard), the opposite of combine-headers' later-wins semantics used elsewhere in provider-utils — porting the wrong one silently breaks user agent/auth overrides. `getTextFromDataUrl` is browser-flavored (`window.atob`) and mediaType-agnostic despite its name.
**Invariant:** Caller headers must always beat defaults or per-call auth/UA customization becomes impossible. The text decoder's two distinct errors (malformed structure vs bad base64) exist so callers can distinguish "not a data URL" from "corrupt payload". Note for porters: this helper does NOT validate that mediaType is text/\* and uses `window.atob` — server-side hosts need the atob/Btoa shim or should reuse splitDataUrl+convertBase64ToUint8Array instead.
**Probe:** No dedicated direct test file at this pin — coverage caveat; behavior pinned via consumer request tests (prepare-step/request fixtures assert UA + custom header coexistence) and `download.test.ts:234` for the data-URL decode path.

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"prepareHeaders defaultHeaders combineHeaders getTextFromDataUrl","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the defaults-fill-gaps merge (and document it against combine-headers to prevent semantic conflation); adapt the browser-only atob call for your runtime before reusing the text decoder; omit it entirely if you already own splitDataUrl-based decoding. Coverage caveat recorded: no dedicated unit suite; verified through consumers.
