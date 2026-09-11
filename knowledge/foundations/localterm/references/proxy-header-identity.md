<!-- capsule-v2 -->
# Proxy-header identity + source-IP allowlist — when does a forwarded user header deserve trust?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you accept `X-Forwarded-User`-style identity from Cloudflare Access/Pomerium/Authelia without letting any direct caller forge it?

## Header honored only inside the trusted-proxy allowlist
**Path/Symbol:** `packages/server/src/identity/header-provider.ts:createHeaderIdentityProvider` (:22–39); `proxy-allowlist.ts:createProxyAllowlist` (:38–67), `normalizeIp` (:8–13), `parseCidr` (:15–26).
**Signature:** `identify(context, sourceIp): Identity | null`; allowlist spec shorthands `"loopback"` (127/8, ::1) | `"private"` (RFC1918+CGNAT+link-local+ULA) | CIDR string | bare address; default spec `loopback`, default header `X-Forwarded-User`.

### Decisive source
```ts
identify: (context: Context, sourceIp: string | null): Identity | null => {
      const value = context.req.header(header);
      if (!value) return null;
      if (!sourceIp || !allowlist.contains(sourceIp)) return null;
      const user = value.trim().slice(0, IDENTITY_USER_MAX_LENGTH);
      return user ? { user } : null;
    },
```
And the dual-stack trap fix:
```ts
// net.BlockList checks family-strict, so a dual-stack listener hands us an
// IPv4-mapped IPv6 address (::ffff:1.2.3.4) that an IPv4 subnet rule would miss.
const normalizeIp = (ip: string): { address: string; family: "ipv4" | "ipv6" } => {
  if (ip.startsWith(IPV4_MAPPED_PREFIX)) {
    return { address: ip.slice(IPV4_MAPPED_PREFIX.length), family: "ipv4" };
  }
  return { address: ip, family: ip.includes(":") ? "ipv6" : "ipv4" };
};
```

**Flow:** request arrives → source IP resolved (raw socket for WS, conninfo for HTTP; read failures resolve null = untrusted = header ignored, never a 500) → header present AND source ∈ allowlist → user trimmed + clamped to 256 chars becomes the Identity; header absent from a TRUSTED proxy resolves null = operator tier (that's the CLI on loopback and the daemon's own CDP tabs keeping full access — hence `denyUnauthenticated: false`).
**Invariant:** trust comes from the socket, never from the header stack: a forged `X-Forwarded-User` from any non-allowlisted interface is ignored wholesale. A missing header over a trusted path is admin parity, not a rejection. IP reads fail OPEN to untrusted (fail-closed for the header, not for availability).
**Probe:** `packages/server/tests/identity.test.ts` :48–107 — loopback matches 127.0.0.2/::1 and rejects 8.8.8.8 :49–55; private shorthand covers RFC1918/CGNAT :57–64; CIDR matches `::ffff:10.5.5.5` after normalization :66–71; bare-address-only match :73–77; identify via REAL Hono `app.request` contexts: trusted IP identifies :81–86, outside-IP ignored :88–91, absent header → operator null :93–96, custom header + CIDR :98–106. Executed this pass, green.
**Retrieve (executed live):**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", name_pattern: "createProxyAllowlist|normalizeIp|parseCidr|createHeaderIdentityProvider", limit: 10 });
```

## Verdict
Adopt source-IP-gated forwarded headers as the zero-login escape hatch behind identity-aware proxies; adopt the IPv4-mapped normalization whenever you touch net.BlockList (family-strict checks silently drop mapped addresses). Adapt the shorthand set to your deployment topologies; omit per-proxy token verification (the proxy's job). Trap: trusting forwarded headers from any local interface, or forgetting that a dual-stack listener hands you ::ffff: addresses.
