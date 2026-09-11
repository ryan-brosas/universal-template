<!-- capsule-v2 -->
# Trusted-proxy client-IP resolution — when may the server believe an X-Forwarded-For style header, and what does a dual-stack listener change?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** How do you take client IPs for rate-limiting and audit without letting any caller spoof them through your proxy header?

## Trust gate before header read
**Path/Symbol:** `src/auth.rs:1069` (`ip_header_is_trusted`), `:1049` (`parse_trusted_proxy`), `:1089-1127` (`FromRequest for ClientIp`), `src/config.rs:673` (`_ip_header_enabled` generated = ip_header != "none").
**Signature:** `fn ip_header_is_trusted(remote: Option<IpAddr>) -> bool`; `parse_trusted_proxy(entry) -> Option<IpNet>` (CIDR or bare IP).
**Data Shape:** `ip_header_trusted_proxies` config: comma list, or special values `all` (trust everyone — explicit footgun switch) and `local` (any non-global remote). Header name itself configurable; `none` disables the whole mechanism.

### Decisive source
```rust
// A dual stack listener reports IPv4 clients as IPv4-mapped IPv6, which `is_global()` reports as
// non global. That is what we want when blocking outgoing requests, but here it would trust them.
let remote = remote.to_canonical();
if trusted.eq_ignore_ascii_case("local") {
    return !crate::util::is_global(remote);
}
trusted.split(',').filter_map(parse_trusted_proxy).any(|net| net.contains(&remote))
```

**Flow:** `ClientIp::from_request`: remote socket → if header enabled AND peer trusted → parse header (first entry only, split on comma for chained proxies; malformed header logs warn and falls back) → else ignore header (debug-log the canonical remote when a header was present but untrusted) → final fallback `remote` then `0.0.0.0`.
**Invariants:** (1) The header is NEVER consulted before the peer passes the trust check — spoofing requires occupying a trusted network. (2) IPv4-mapped IPv6 MUST be canonicalized before `is_global`-style tests, else `::ffff:x.x.x.x` peers misclassify; note the SAME canonicalization serves the opposite polarity in http_client egress blocking. (3) Untrusted-but-present headers produce a debug line naming the ignored value — auditability without behavior change.
**Probe:** `grep -n 'to_canonical()' src/auth.rs | wc -l` → `2` (trust check + ignore-log).

## is_global twin implementation
**Path/Symbol:** `src/util.rs:851` (`is_global_hardcoded`), `:911-915` (feature-gated std swap).
**Data Shape:** full hand-rolled global-address predicate (v4 shared/benchmarking/reserved blocks; v6 64:ff9b:1/48, 100::/64, 2001::/23 minus anycast exceptions, 5f00::/16 SRv6…); under feature `unstable` it re-exports `std::net::IpAddr::is_global`, kept honest by exhaustive `#[ignore]` fuzz tests (util.rs:942-990).
**Probe:** `grep -c 'is_global_hardcoded' src/util.rs` → `4`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "ip_header_is_trusted", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt peer-trust-gated header parsing with first-entry-only semantics; adapt the config surface (names, special values) to your product; omit the `local` shorthand if you lack an is_global equivalent. Source confirmed at pin; no direct upstream test outside the unstable fuzz pair.
