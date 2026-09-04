<!-- capsule-v2 -->
# Raw TLS client — how does the browserless path present a Chrome-consistent TLS+header fingerprint?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** How are TLS profiles, UA-CH headers, and header ORDER kept coherent without a real Chrome, and how is SSRF guarded across redirects?

## tls-client wrapper
**Path/Symbol:** `core/http_client.go` (whole file): rawChromeProfiles/pickRawChromeProfile (L28–46), rawHeaderOrder (L48–63), cachedRawHTTPClient (L252–284), rawRequestProfileFor/applyRawChromeMajor (L378–440), applyRawRequestHeaders (L478–508), doGuardedRawRequest (L142–171), ClassifySearchHTTPStatus (L209–225).
**Signature:** `RawSearchRequest(ctx, url, Query) (*http.Response, error)`; `pickRawChromeProfile(salt) (int major, profiles.ClientProfile)`; `cachedRawHTTPClient(query, profileKey, tlsProfile)`.
**Data Shape:** profiles {133, 144, 146}; client LRU cache max 64 keyed (proxyURL, full header profile, insecure, guard); rawHTTPTimeout 30s.

### Decisive source
```go
// pick by FNV-1a of lane salt so a session keeps ONE coherent fingerprint:
h := fnv.New32a(); h.Write([]byte(salt))
p := rawChromeProfiles[int(h.Sum32()) % len(rawChromeProfiles)]
...
req.Header[fhttp.HeaderOrderKey] = rawHeaderOrder   // tls-client profiles don't order headers
for _, h := range [][2]string{
	{"User-Agent", profile.userAgent},
	{"Accept", "text/html,...image/apng,*/*;q=0.8"},
	{"Accept-Language", ...}, {"Upgrade-Insecure-Requests","1"},
	{"Sec-CH-UA", formatSecCHUA(brands)}, {"Sec-CH-UA-Mobile","?0"}, {"Sec-CH-UA-Platform",...},
	{"Sec-Fetch-Site","none"},{"Sec-Fetch-Mode","navigate"},{"Sec-Fetch-User","?1"},{"Sec-Fetch-Dest","document"},
} { ... }
// SSRF: WithNotFollowRedirects + manual loop validating EVERY hop:
for hop := 0; ; hop++ {
	if err := ValidatePublicHTTPURL(ctx, current); err != nil { return nil, err }
	resp = doRawRequest(...)
	location, ok := redirectLocation(resp); if !ok { return resp }
	if hop >= maxGuardedRedirects { return ErrEngineInternal }
	current = resolveRedirectURL(current, location)
}
```
GuardedDialContext (network_guard.go) resolves DNS itself and dials the vetted public IP — DNS rebinding can't swap a private address between validation and dial; validatePublicHost fails closed on ANY non-public record (Chrome path resolves its own DNS). ErrTargetNotAllowed marks policy rejections → 400 invalid_extract_url.
**Invariant:** proxy errors classified ONLY when proxied (execRawRequest); response bodies wrapped in networkUsageReadCloser to attribute bytes to the request context; DrainAndCloseResponse before reusing keep-alive connections.
**Probe:** `go test ./core -run 'TestHTTP|TestNetworkGuard'` (http_client_test.go + network_guard_test.go pin classification and guard behavior).
**Probe executed (real runner):** the written pattern matches ZERO tests — repaired: `go test ./core -run 'TestRawHTTPClient|TestValidatePublicHTTPURL'` = **6 PASS** at pin (TLS/HTTP2 negotiation, header defaults, proxy-auth classification, socks5h proxy-DNS, private-IP guard incl. bare-IP normalization).
**Python-equivalent probe (executed):**
```python
def fnv32a(s):
    h=0x811c9dc5
    for b in s.encode(): h=((h^b)*0x01000193)&0xffffffff
    return h
profiles=[133,144,146]
salt="google:de"
print("profile pick GREEN:", profiles[fnv32a(salt)%3], "for salt", salt)
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "pickRawChromeProfile applyRawRequestHeaders GuardedDialContext ValidatePublicHTTPURL ClassifySearchHTTPStatus", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt salt-stable profile picking, fixed header order, and per-hop guarded redirects for any server-side fetcher; refresh the Chrome preset list as tls-client ships them; omit the byte-attribution wrapper if you don't expose X-Network-Bytes.
