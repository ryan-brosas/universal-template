<!-- capsule-v2 -->
# Domain extraction boundaries — which inputs must yield EMPTY domains, and why is subdomain matching suffix-anchored?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** What are the acceptance rules for URL→domain, and how are phishing look-alikes (`example.com.evil.com`) excluded?

## Acceptance ladder
**Path/Symbol:** `core/rust/src/credential_matcher/domain.rs:124-222` (`extract_domain_with_port`), :235-258 (`extract_root_domain`), :262-297 (`domains_match`, `is_subdomain_of`).
**Signature:** `pub fn extract_domain_with_port(url: &str) -> DomainWithPort { domain: String, port: Option<String> }`.
**Data Shape:** Rejects: empty; package names (TLD first label, no protocol); no-dot hostnames WITHOUT protocol (random text); non-[alnum.-] characters; leading/trailing dots or `..`. Accepts single-word hostnames WITH protocol (`http://plex` — homelab contract); strips protocol/www/path/query/# before numeric-port validation.

### Decisive source
```rust
// - If URL had a protocol (http:// or https://), allow single-word hostnames
//   like "localhost", "plex", "nas", "router" - common in self-hosted/homelab setups
// - If no protocol, require at least one dot to distinguish from random text
if !domain.contains('.') && !has_protocol {
    return DomainWithPort { domain: String::new(), port: None };
}
...
fn is_subdomain_of(domain1: &str, domain2: &str) -> bool {
    // Check if domain1 ends with ".domain2" (proper subdomain boundary)
    domain1.ends_with(&format!(".{}", domain2))
}
```

**Flow:** root-domain uses a hardcoded TWO_LEVEL_TLDS table (~150 entries: co.uk, com.au, …): last-two-labels ∈ table ⇒ keep THREE labels, else two → match ladder is exact ⇒ proper-suffix subdomain ⇒ equal roots — so `sub.example.com`~`www.example.com` match via root, while `another-example.com`, `myexample.com`, and `example.com.evil.com` all FAIL against `example.com`.
**Invariants:** (1) Subdomain check requires the FULL label boundary `.domain2` suffix with strictly-greater length — substring containment would match `another-example.com`. (2) The evil-twin case fails because its ROOT is `evil.com`. (3) Port must be all-digits else dropped (`https://example.com:abc` ⇒ port None, domain kept). (4) Protocol presence is what legalizes dot-less hostnames; the same string bare stays empty.
**Probe:** `grep -c '!domain.contains' core/rust/src/credential_matcher/domain.rs` → `1`; `grep -c 'example.com.evil.com' core/rust/src/credential_matcher/domain.rs` → `1`; `grep -c 'parts\[parts.len() - 3..\]' core/rust/src/credential_matcher/domain.rs` → `1`.

## Direct tests
**Path/Symbol:** in-file tests :300-458 pin every boundary incl. `test_extract_domain_single_word_hostname_with_port` (:351) and anti-phishing asserts :448-456.
**Probe:** run upstream cargo test where toolchain exists; deterministic probes above executed at pin `95903e92`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "extract_root_domain", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the acceptance ladder + suffix-anchored subdomain logic + static two-level-TLD table; swap in a public-suffix list if your scope demands it (upstream chose static deliberately); omit Rust specifics. In-file tests exist but were not executed here.
