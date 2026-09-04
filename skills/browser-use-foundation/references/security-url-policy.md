<!-- capsule-v2 -->
# Security watchdog — 3-tier URL allow/block policy with WHATWG IP canonicalization

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does a browser agent enforce a URL allow/block policy that can't be bypassed by IP-encoded or glob patterns?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/watchdogs/security_watchdog.py` (296 lines): `SecurityWatchdog` (:22) — `on_NavigateToUrlEvent` (:35-48, pre-nav block), `on_NavigationCompleteEvent` (:50-71, redirect catch → about:blank), `on_TabCreatedEvent` (:73-92, close offending tab), `_is_url_allowed` (:176-250), `_is_url_match` (:252-296), `_is_ip_address` (:138-174), `_get_domain_variants` (:122-136), `_is_root_domain` (:94-110).
**Signature:** `_is_url_allowed(url) -> bool`; `_is_ip_address(host) -> bool`.

### Decisive source
```python
# 1. always allow internal targets (about:blank, chrome://new-tab-page) FIRST
# 2. data:/blob: always allowed (no hostname)
# 3. if block_ip_addresses: _is_ip_address(host) -> False  (WHATWG canonicalization)
#   - ipaddress.ip_address (IPv4/IPv6) OR socket.inet_aton (liberal decimal/hex/octal/short-form)
#   - NFKC-normalize + unquote percent-encoding + IDNA separators (。｡ -> .) BEFORE checking
# 4. no allow/prohibit configured -> allow all
# 5. allowed_domains set -> O(1) exact hostname (www + non-www variants); list -> O(n) pattern match
# 6. prohibited_domains set -> O(1) exclusion; list -> O(n) pattern
# Pattern match (_is_url_match): glob (*.example.com matches subdomain+main; scheme-http-only for
#   domain patterns; */* path patterns via fnmatch; exact URL or host match; root-domain www alias)
```

**Flow:** pre-nav check blocks disallowed URLs (raises ValueError to stop propagation); post-nav check catches redirects → dispatches `BrowserErrorEvent` + navigates to about:blank to keep the session alive; new-tab check closes the offending tab. IP blocking runs BEFORE domain checks (an IP can't be whitelisted via allowed_domains).
**Invariant:** `_is_ip_address` never raises (unrecognizable hosts return False and fall to domain handling); NFKC + percent-decode + `inet_aton` close the decimal/hex/octal/short-form/IPv4-encoding bypass (mirrors WHATWG host canonicalization); `block_ip_addresses` beats `allowed_domains` (IPs blocked even if listed).
**Probe:** `tests/ci/security/test_ip_blocking.py` (lines 503-609: decimal/hex/octal/short-form/percent-encoded/NFKC cases), `tests/ci/security/test_domain_filtering.py`, `tests/ci/security/test_mcp_allowed_domains.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "SecurityWatchdog _is_url_allowed _is_ip_address inet_aton NFKC allowed_domains", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the 3-tier policy (internal→IP-block→domain), the WHATWG-canonicalizing IP classifier (inet_aton + NFKC + percent-decode), and the glob semantics. This is the SSRF/redirect-bypass hardening a porter would otherwise get wrong.
