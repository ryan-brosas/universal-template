<!-- capsule-v2 -->
# Client-IP resolution ladder — how do you find the real client IP behind arbitrary CDN/proxy stacks without trusting spoofable headers?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** In what priority order are IP headers consulted and how are IPv4-mapped/ported/garbage values normalized?

## client-ip-ladder
**Path/Symbol:** `src/lib/ip.ts:IP_ADDRESS_HEADERS :3-18, normalizeIp :19-34, resolveIp :36-56, parseHeaderValue :58-65, getIpAddress :75-88, stripPort :90-110`; direct tests `src/lib/ip.test.ts:12-80`.
**Signature:** `getIpAddress(headers: Headers) -> string | undefined`; first PRESENT header in priority list wins.
**Data Shape:** priority list (cloud-mode custom first) → `true-client-ip`, `cf-connecting-ip`, `fastly-client-ip`, `x-nf-client-connection-ip`, `do-connecting-ip`, `x-real-ip`, `x-appengine-user-ip`, then `x-forwarded-for` / `forwarded` / remaining x-* aliases.

### Decisive source
```ts
if (header === 'x-forwarded-for') {
  return resolveIp(value?.split(',')?.[0]?.trim());       // LEFTMOST = original client
}
if (header === 'forwarded') {
  const match = value.match(/for=(\[?[0-9a-fA-F:.]+]?)/); // RFC 7239 extraction
  return match ? resolveIp(match[1]) : undefined;
}
// resolveIp: try parse → else strip port → re-parse; normalizeIp maps ::ffff:a.b.c.d → a.b.c.d
```

**Flow:** optional CLIENT_IP_HEADER override → walk fixed priority list → per-header parsing rule → normalization pipeline (parse, compress IPv6, unmap v4-in-v6, strip `:port`) → garbage passes through UNCHANGED as final fallback (caller-side validation like `ipaddr.isValid` decides usability).
**Invariant:** leftmost-XFF is the spoofable-but-correct choice for analytics (umami accepts the risk; geo only feeds stats) — a security decision, not an accident. Vendor headers rank ABOVE XFF because proxies overwrite them; the custom CLOUD_MODE header ranks above all because only the platform can set it.
**Probe:** `grep -c "test(" src/lib/ip.test.ts` → 19; named cases pin forwarded RFC7239 (:39), vendor-over-XFF preference (:45), v6 compression (:53), v4-mapped conversion (:59), port strip (:63), garbage passthrough (:67).
**Probe:** `grep -n "prefers higher-priority" src/lib/ip.test.ts` → :45.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "getIpAddress normalizeIp stripPort forwarded", limit: 10 });
```

## Verdict
Adopt the ordered-header + normalization ladder for any client-metadata collection; reorder to YOUR edge stack; if you feed IPs into security controls instead of analytics, invert to rightmost-trusted-proxy semantics.
