<!-- capsule-v2 -->
# SECURITY-CRITICAL domain-pattern URL matching — how do you gate which domains an agent may act on without wildcard abuse?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does a glob-ish domain allowlist match URLs safely, and which wildcard shapes must be refused?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/utils.py` — `match_url_with_domain_pattern` (:531, marked "SECURITY CRITICAL"), `is_unsafe_pattern` (:497), `is_new_tab_page` (:518), `is_placeholder_url` (:28), `sanitize_url_candidate` (:42).
**Signature:** `match_url_with_domain_pattern(url: str, domain_pattern: str, log_warnings: bool = False) -> bool`.

### Decisive source
```python
# Supported shapes:
#   *.example.com  -> sub.example.com AND example.com (special parent-domain case)
#   *google.com    -> google.com, agoogle.com, www.google.com (prefix glob)
#   http*://x.com  -> scheme glob
#   chrome-extension://* -> any extension id
# Refused shapes (return False + log):
#   multiple wildcards (*.*.domain), wildcard TLDs (example.*),
#   embedded wildcards not of *.domain form
if '://' in domain_pattern:
    pattern_scheme, pattern_domain = domain_pattern.split('://', 1)
else:
    pattern_scheme = 'https'   # NO SCHEME => HTTPS-ONLY for security:
    pattern_domain = domain_pattern   # 'example.com' matches https but NOT http
if not fnmatch(scheme, pattern_scheme): return False
if is_new_tab_page(url): return False   # about:blank/chrome:// handled at CALLSITE, never matched here
```

**Flow:** parse URL to lowercase hostname+scheme only (ports stripped from patterns; auth/query ignored) → pattern normalized; missing scheme pins https → scheme fnmatch → exact match or vetted glob ladder (`*.domain` also matches bare parent) → any exception returns False (fail-closed). Companions: `is_placeholder_url` detects mock hosts like `XXX.XX` (all-x labels); `sanitize_url_candidate` strips escaped-newline task prose and trailing punctuation from LLM-extracted URLs before navigation.
**Invariant:** default-scheme must be https (an http-default would let patterns silently bless plaintext); new-tab pages are deliberately OUT of scope here — callers must special-case them or blank-tab flows break; unsafe wildcard classes refuse-to-match rather than degrade to substring matching.
**Probe:** `tests/ci/security/test_sensitive_data.py` — `test_match_url_with_domain_pattern` (:101), `test_unsafe_domain_patterns` (:137), `test_malformed_urls_and_patterns` (:156), `test_is_new_tab_page` (:260).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "match_url_with_domain_pattern is_unsafe_pattern is_placeholder_url sanitize_url_candidate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the matcher whole (scheme-pinning, refusal matrix, fail-closed exception path); adapt the accepted-shape list to your product's allowlist UX; omit benchmark-prose URL cleaning if unused.
