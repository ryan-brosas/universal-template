<!-- capsule-v2 -->
# Internal HTTP proxy plane — how do you forward authenticated requests between your own servers safely?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you proxy requests to internal workers carrying cookies/org headers without creating proxy loops, header leaks, or letting a crafted URL re-route credentials to an attacker host?

## Transitive allowlist + stamped one-hop guard + origin-locked target URL + hop-by-hop stripping both directions
**Path/Symbol:** `app/server/lib/requestUtils.ts`: `GRIST_PROXIED_HEADER` + `hasAlreadyProxiedHeader` (642–649), `getProxyHeaders` (678–710), `HOP_BY_HOP_HEADERS` + `stripHopByHopHeaders` (713–741), `openUpstream` (780–804), `proxyHttpRequest` settle-latch (871–966), `forwardHttpRequest` buffered twin (840–859), `relayBufferedResponse` (823–827), `buildProxyPath` (993–1001), `buildProxyRequestUrl` origin-escape guard (1011–1019), `terminateSocketWithHttpResponse` (656–668); tests `test/server/lib/requestUtils.ts`.
**Signature:** `proxyHttpRequest(clientReq, clientRes, targetUrl: string | URL, options?: ProxyHttpRequestOptions): Promise<void>`; options `{ forbidHeaders?: Lowercase<string>[], proxyExtraHeaders?, defaultHeaders?, omitOrigin? }`.
**Data Shape:** forwarded set = transitive auth headers + accept-language/content-type (+ extras) + defaults; loop guard = literal `x-grist-proxied: true`.

### Decisive source
```ts
// buildProxyRequestUrl — the anti-reroute guard:
const composed = `${target.origin}${buildProxyPath(target, reqUrl)}`;
const parsed = new URL(composed);
if (parsed.origin !== target.origin) {
  throw new Error(`final proxy URL escaped target origin: ${target.origin} -> ${parsed.origin}`);
}
// e.g. a request URL of  //evil.example/x  would make new URL(target, base) swap authorities;
// composing from target.origin FIRST and re-checking keeps the target fixed.

// stripHopByHopHeaders also honors Connection-named tokens:
if (headers["transfer-encoding"]) { dynamic.add("content-length"); } // RFC 7230 §3.3.3
```

**Flow:** caller derives target from config (NEVER user input) → `getProxyHeaders` lowercases transitive headers, stamps x-grist-proxied, adds accept-language/content-type/extras/defaults, deletes forbidHeaders, strips hop-by-hop → `openUpstream` refuses any protocol outside http/https and issues http.request with `timeout: 0` (client-side disconnect is the abort signal) → streaming path pipelines body up and response down with ONE centralized `settle(err?)` latch (`isSettled` guards double-settle from destroy cascades; failure path writes 502 if headers unsent else destroys, always try/except-guarded because it runs from disconnect handlers) → upgrade attempts are destroyed with a 502-style error since Upgrade is never forwarded → buffered path (`forwardHttpRequest`) returns `{status, headers(stripped), text}` decoded utf8 (callers must NOT forward accept-encoding to it) and `relayBufferedResponse` re-strips before replying ("worth it to keep a relay safe on its own terms").
**Invariant:** targetUrl must never be user-influenced (credential theft) and the composed URL must land on the target origin (authority-swap defense); a request may be proxied AT MOST once (deployments strip x-grist-proxied at the LB — spoofable header, documented SECURITY note); no redirects are followed on the buffered path (forwarded credentials stay on the intended host); hop-by-hop stripping happens on BOTH directions plus again at relay.
**Probe:** `test/server/lib/requestUtils.ts` — hostile-input origin guard :77, /dw-/v-strip + query preservation :83, header forwarding/stripping/defaults :129–161, hop-by-hop both directions :170, 502-on-unreachable :217, 101-protocol-switch refusal :231, invalid-protocol rejection :261, client-abort propagation :272, buffered send/relay/cleanup :337–362.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "proxyHttpRequest getProxyHeaders buildProxyRequestUrl stripHopByHopHeaders", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any multi-service deployment that forwards logged-in traffic internally: the stamped one-hop guard + origin-locked composition + bidirectional hop-by-hop hygiene are directly portable. Adapt the forwarded-header list to your auth surface and consider replacing the spoofable stamp with a Permit-style secret signature (noted future improvement upstream). Omit the raw-socket responder unless you own an upgrade handler.
