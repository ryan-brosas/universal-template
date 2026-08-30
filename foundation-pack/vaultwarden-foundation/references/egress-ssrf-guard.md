<!-- capsule-v2 -->
# Egress SSRF guard — how does a server-side fetcher make DNS rebinding and redirect escapes impossible?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** Where must private-IP blocking hook into an HTTP client so both direct URLs and redirect chains are covered?

## Block at URL-parse, at every DNS answer, at every redirect hop
**Path/Symbol:** `src/http_client.rs:19-33` (`make_http_request`), `:35-59` (`get_reqwest_client_builder` custom redirect policy), `:137-158` (`should_block_host`), `:274-290` (`CustomDnsResolver::resolve_domain` pre/post resolve), `:292-315` (`pre_resolve`/`post_resolve`), `src/util.rs:851` (`is_global` predicate).
**Signature:** `pub fn should_block_host<S: AsRef<str>>(host: &Host<S>) -> Result<(), CustomHttpClientError>`; `fn should_block_ip(ip) -> bool { !CONFIG.http_request_block_non_global_ips() ? false : !is_global(ip) }`.

### Decisive source
```rust
let redirect_policy = reqwest::redirect::Policy::custom(|attempt| {
    if attempt.previous().len() >= 5 { return attempt.error("Too many redirects"); }
    let Some(host) = attempt.url().host() else { return attempt.error("Invalid host"); };
    if let Err(e) = should_block_host(&host) { return attempt.error(e); }   // re-check EVERY hop
    attempt.follow()
});
Client::builder().default_headers(headers).redirect(redirect_policy)
    .dns_resolver(CustomDns::instance(enforce_block))   // resolution itself is intercepted
    .timeout(Duration::from_secs(10))
```
```rust
// post_resolve: the resolved IP is checked with the ORIGIN domain attached for diagnostics
should_block_host(&host).map_err(|e| e.with_domain(name))
```

**Flow:** caller → parse URL → `should_block_host` (literal IPs blocked immediately; domains pass to regex blocklist check) → reqwest calls the CUSTOM resolver → `pre_resolve` re-validates hostname grammar + blocklist → DNS answers (ALL of them — the results Vec is iterated) each go through `post_resolve` → only then connect. Redirects re-enter `should_block_host` per hop.
**Invariants:** (1) Checking at resolve time kills DNS REBINDING: an attacker can't return a private IP on the second lookup because every returned address is screened, and reqwest connects to the resolver's vetted addresses only. (2) Blocking is config-gated (`http_request_block_non_global_ips`) so self-hosted intranet icon fetching can be deliberately enabled; regex blocklist has its own switch and is compiled once per value change (Mutex<Option<(String,Regex)>> memoization :74-92). (3) Error type carries the offending DOMAIN through `with_domain` even when the trigger was the resolved IP.
**Probe:** `grep -c 'post_resolve(name' src/http_client.rs` → `2` (definition + call inside the resolve-answer loop).

## Host grammar hardening
**Path/Symbol:** `http_client.rs:94-135` (`get_valid_host`).
**Data Shape:** after url::Host::parse: length ≤253; labels non-empty ≤63 no leading/trailing hyphen ASCII-alnum+hyphen only (input already punycoded). Prevents header-injection-style hostnames reaching the resolver.
**Probe:** `grep -c 'exceeds 253 characters' src/http_client.rs` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "should_block_host", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-hook placement (parse / resolve-answer / redirect-hop); adapt to your client's DNS-extension API; omit hickory fallback specifics but keep IPv4-first ordering awareness (`DNS_PREFER_IPV6` interplay :258-265).
