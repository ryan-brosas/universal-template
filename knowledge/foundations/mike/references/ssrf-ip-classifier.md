<!-- capsule-v2 -->
# SSRF IP classifier — which address literals must an outbound-fetch guard reject, fail-closed?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** How does a server classify a resolved IP literal as private/reserved/unsafe — including IPv6 transition ranges that hide IPv4 targets — so every egress caller rejects the same set?

## BlockList tables + global-unicist gate + embedded-v4 re-classification
**Path/Symbol:** `backend/src/lib/privateIp.ts:42` (`isPrivateIpv4`), `:54` (`expandIpv6Groups`), `:96` (`isPrivateIpv6`), `:141` (`isBlockedIp`). Direct test: `backend/src/lib/__tests__/privateIp.test.ts` + SSRF integration test `src/lib/mcp/__tests__/client.ssrf.test.ts`.
**Signature:** `isBlockedIp(ip) -> boolean`; non-IP input returns **true** (fail closed).
**Data Shape:** two prebuilt `net.BlockList`s — 16 IPv4 subnets (unspecified 0/8, RFC1918 ×3, CGNAT 100.64/10, loopback, link-local 169.254/16, IETF 192.0.0/24, TEST-NET ×3, 6to4 anycast, benchmarking 198.18/15, multicast 224/4, reserved 240/4) and 6 IPv6 doc/transition blocks.

### Decisive source
```ts
// ::/96 (v4-compatible) and ::ffff:0:0/96 (v4-mapped) are NOT globally
// reachable — block ENTIRE ranges even when the embedded v4 is public.
if (groups.slice(0, 6).every((g) => g === 0)) return true;
if (groups.slice(0, 5).every((g) => g === 0) && groups[5] === 0xffff) return true;
// NAT64 64:ff9b::/96 IS globally reachable → decide by the EMBEDDED IPv4:
if (groups[0] === 0x64 && groups[1] === 0xff9b /* …zeros… */)
    return isPrivateIpv4(embeddedIpv4(groups[6], groups[7]));
const isGlobalUnicast = (groups[0] & 0xe000) === 0x2000; // 2000::/3 only
if (!isGlobalUnicast) return true; // fc00::/7, fe80::/10, ff00::/8, 100::/64…
```

**Flow:** dotted-quad tails (`::ffff:1.2.3.4`) are folded into two hextets before group counting; zone ids (`%eth0`) stripped before parsing; `::` expansion rejects >1 occurrence and wrong final count (must be 8 groups); octets >255 in a v4 tail invalidate.
**Invariant:** Unparseable/unrecognized ⇒ blocked (never "allow on doubt"). The v4-mapped/v4-compatible whole-range block is deliberate: allowing them because the embedded v4 "looks public" would let an attacker reach host-local services via translation semantics. NAT64 is the ONLY translation prefix whose target gets a second chance, because the prefix itself is globally routable.
**Probe:** `grep -c 'it.each' src/lib/__tests__/privateIp.test.ts` → 5 parametrized matrices (16 blocked v4, 18 blocked v6 incl `::ffff:8.8.8.8`, `64:ff9b::10.0.0.1`, `64:ff9b:1::1`; allow-list arms for global v4/v6); `grep -c 'resolvesTo' src/lib/mcp/__tests__/client.ssrf.test.ts` shows the egress-side harness consuming the same classifier.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "isPrivateIpv6 BlockList SSRF blocked IP", limit: 10 });
```

## Verdict
Adopt fail-closed-on-doubt + whole-range blocking of v4-embedded families + NAT64 re-classification + 2000::/3 allowlist gate as portable contracts; adapt the range table to your threat model and DNS-resolution layer (callers pass RESOLVED literals); omit Node `net.BlockList` mechanics.
