<!-- capsule-v2 -->
# Autofill priority ladder with anti-phishing URL gate — in what order are credentials offered, and which credentials may NEVER match by name?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** What is the exact early-return ladder, and why do URL-less credentials behave differently?

## Priority-ordered filter
**Path/Symbol:** `core/rust/src/credential_matcher/mod.rs:99-402` (`filter_credentials`), doc ladder :5-11, cap :26 (`DEFAULT_MAX_RESULTS: usize = 10`).
**Signature:** `pub fn filter_credentials(input: CredentialMatcherInput) -> CredentialMatcherOutput { matched_ids: Vec<String>, matched_priority: u8 /* 1..4, 0=none */ }`.
**Data Shape:** Input: credentials (multi-URL via `item_urls: Vec<String>`), current_url, page_title, matching_mode (Default|UrlExact|UrlSubdomain), ignore_port (Android), max_results. Ladder: P1 app-package exact → P2 URL domain (sub-priorities 1 domain+port / 2 domain / 3 subdomain-root) → P3b root-domain-word vs item names → P3 page-title vs names (ONLY when domain extraction FAILED) → P4 text words.

### Decisive source
```rust
// SECURITY: Skip credentials that have URLs defined   ← appears at BOTH name-matching priorities
if !cred.item_urls.is_empty() && cred.item_urls.iter().any(|u| !u.is_empty()) {
    return false;
}
...
.filter(|word| word.len() > 3 && !stop_words.contains(*word))
```
```rust
// Only return credentials at the best priority level — if we have exact domain+port matches (1),
// we only show those; exact-domain (2) hides subdomain (3) matches.
let filtered_by_priority: Vec<CredentialWithPriority> =
    filtered.into_iter().filter(|c| c.priority == best_priority).collect();
```

**Flow:** empty URL ⇒ priority 0 immediately → package-name input skips URL matching entirely (falls to P4 on no-match) → URL path computes per-credential BEST sub-priority across all its URLs (`break` rules: port-exact stops scanning; domain-exact keeps looking unless ignore_port) → any URL matches ⇒ return ONLY the best-priority tier, deduped by id, capped at max_results → NO url matches ⇒ P3b/P3 word fallback restricted to URL-less credentials → P4 unrestricted text search last.
**Invariants:** (1) The anti-phishing rule: a credential WITH URLs can never surface from a title/name match — prevents `evil.com` page titles from offering your real bank entry. (2) Best-tier filtering means one exact-match credential HIDES weaker subdomain matches rather than mixing. (3) Word extraction drops ≤3-char tokens + stop words; comparisons are whole-word equality, never substrings. (4) Package-name detection is TLD-first-label based (`com.foo.bar`) — see domain-extraction-boundaries capsule.
**Probe:** `grep -c 'DEFAULT_MAX_RESULTS: usize = 10' core/rust/src/credential_matcher/mod.rs` → `1`; `grep -c 'matched_priority: 3' core/rust/src/credential_matcher/mod.rs` → `2`; `grep -c 'SECURITY: Skip credentials that have URLs defined' core/rust/src/credential_matcher/mod.rs` → `2`; `grep -c 'word.len() > 3' core/rust/src/credential_matcher/mod.rs` → `1`.

## Direct tests
**Path/Symbol:** `core/rust/src/credential_matcher/tests.rs` (upstream suite driving every priority branch); module header documents the spec (:5-11).
**Probe:** run upstream cargo test where toolchain exists; deterministic probes above executed at pin `95903e92`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "filter_credentials", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered ladder + best-tier-only output + the URL-having-credentials exclusion from name matches; adapt stop-word list; omit platform plumbing. In-file Rust tests exist but were not executed here.
