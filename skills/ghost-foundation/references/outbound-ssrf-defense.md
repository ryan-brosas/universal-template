<!-- capsule-v2 -->
# Outbound SSRF defense-in-depth — how is a user-supplied URL prevented from reaching private networks?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** Where in the request lifecycle are private-IP checks applied so DNS rebinding can't slip between check and connect?

## request-external
**Path/Symbol:** `ghost/core/core/server/lib/request-external.js:isPrivateIp` (:110–182), `errorIfHostnameResolvesToPrivateIp` (:185–209), `installSafeDnsLookup` (:242–292), hook wiring (:300–316).
**Signature:** got instance with `hooks.beforeRequest = [errorIfInvalidUrl, errorIfHostnameResolvesToPrivateIp, installSafeDnsLookup]` and `hooks.beforeRedirect = [errorIfHostnameResolvesToPrivateIp, installSafeDnsLookup]`.
**Data Shape:** Private set (IPv4): 10/8, 172.16–31, 192.168/16, 127/8, 169.254/16, 100.64/10 CGNAT, 198.18/15 benchmarking, 0/8, 240/4+broadcast; IPv6: ::1, ::, fc00::/7 ULA, fe80::/10 link-local; plus ALL IPv4-mapped forms (::ffff:dotted, ::ffff:hex, expanded) re-checked after normalization. Handles decimal/octal/hex/integer host encodings by normalizing through WHATWG URL parser.
### Decisive source
```js
options.dnsLookup = (hostname, dnsOpts, callback) => {
  dns.lookup(hostname, dnsOpts, (err, addressOrResult, family) => {
    ...
    if (isPrivateIp(addressOrResult)) {
      return callback(new errors.InternalServerError({ message: 'URL resolves to a non-permitted private IP block', code: 'URL_PRIVATE_INVALID', ...}));
    }
    callback(null, addressOrResult, family);
  });
};
```
**Flow:** beforeRequest does a first-pass DNS resolve + validation with clear errors → then installs a custom native `lookup` option so the IP Node actually CONNECTS to is the one just validated → same pair re-applies on EVERY redirect hop. Dev-mode and the site's own hostname are exempt (self-references allowed).
**Invariant:** The beforeRequest check alone has a TOCTOU gap (DNS may answer differently at connect); the authoritative gate is `dnsLookup` at connection layer — a porter who keeps only the pre-check has NOT ported the defense. Fail-closed everywhere: empty/unrecognized/unparseable ⇒ treated private. Shared keep-alive agents pool sockets across page renders/oEmbed/recommendations to survive NAT connection-rate ceilings.
**Probe:** `grep -cF "installSafeDnsLookup" ghost/core/core/server/lib/request-external.js` → expect `5`; `grep -cF "beforeRedirect: [errorIfHostnameResolvesToPrivateIp, installSafeDnsLookup]" ghost/core/core/server/lib/request-external.js` → expect `1`; `grep -cF "return true;" ghost/core/core/server/lib/request-external.js` → expect `16`; direct tests: `grep -cF "it('treats unrecognized format as private (fail closed)'" ghost/core/test/unit/server/lib/request-external.test.js` → expect `1`; `grep -cF "dnsLookup blocks private IPs" ghost/core/test/unit/server/lib/request-external.test.js` → expect `2` (it + loopback variant).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "errorIfHostnameResolvesToPrivateIp dns", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-layer (pre-check + connection-time lookup) pattern with redirect re-checks and fail-closed normalization. Adapt the range list to host policy; omit got-specific plumbing if using another client but keep a connection-layer gate.
