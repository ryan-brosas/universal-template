<!-- capsule-v2 -->
# browser-use allowlist normalization: scheme-qualify host entries so file:// can never ride an allowlist

## Source / Question
`pydantic_ai_harness/browser_use/_toolset.py:24–190, 420–520` @ `main@f971198` (PR #9989) — browser-use consults `allowed_domains` OR `prohibited_domains`, never both: a non-empty allowlist short-circuits the prohibition list. So a plain hostname allowlist entry matches by hostname REGARDLESS of scheme and would admit `file://` — overriding local-file prohibition entirely. How do you normalize entries so intent survives?

## Path / Symbol
`browser_use/_toolset.py` — `_LOCAL_FILE_PATTERNS=['file://*']` / `_HTTP_SCHEME_GLOB='http*'` (:24–25), `_strip_trailing_dot` (:29–39), `_restrict_to_http_schemes` (:42–48), `_normalize_allowed_domain(s)` (:51–86), `_glob_hostname` hand-parsed authority (:131–144), `_pattern_allows_localhost` (:147–162), `_exclude_localhost_allowlist_entries` overloads (:165–186), `_kill` shielded teardown (:188+), profile assembly in session factory (:495–520).

## Signature
```python
def _normalize_allowed_domain(domain: str) -> list[str]:
    if '://' in domain:
        scheme, rest = domain.split('://', maxsplit=1)
        if fnmatch('file', scheme.lower()):
            return [f'{m}://{rest}' for m in ('http', 'https') if fnmatch(m, scheme.lower())]
        ...                                  # http(s)+host-only entry → f'{domain}/*'; others untouched
    if domain.startswith('*.'): return [domain]     # browser-use restricts these to http/https itself
    return _restrict_to_http_schemes(domain)        # bare host → ['http*://host' (+ www variant when 1 dot, no '*')]
```

## Data Shape
Normalization runs in BOTH `BrowserUse.__post_init__` (report bad allowlists at construction) and the toolset (covers directly-built toolsets); idempotent so both layers compose. A file-only allowlist (`['file://*']`) normalizes to EMPTY and raises `ValueError(_FILE_SCHEME_ALLOWLIST_ERROR)`.

### Decisive source
Scheme-narrowing precision rule (:60–66 docstring): "a glob can admit `file` and only one of the two (`????` matches `http` but not `https`), and widening to both would newly permit a scheme the caller never allowed" — hence explicit per-matched-scheme emission instead of one `http*`. `urlsplit` unusable for pattern hosts: rejects `[ab]*.example.com` as malformed IPv6 and can't parse `http*://` schemes ⇒ authority split BY HAND with bracket-aware port strip (:135–143). localhost exclusion under `block_ip_addresses`: `<label>.localhost` is loopback per RFC 6761 "without resembling any sample", so the suffix is tested directly against representative hosts `('localhost','localhost.example','example.localhost')` (:150–161); a localhost-ONLY allowlist raises demanding `block_ip_addresses=False` (:184). Teardown shield `_kill` (:189+): `BrowserSession.kill` suspends several times over CDP; unshielded, first await inside a cancelled scope leaves a LIVE Chromium holding a `user_data_dir` lock — wrapped in `anyio.CancelScope(shield=True)` + bounded timeout, failures swallowed-and-logged ("retaining the session for retry") because it runs in `finally`.

**Flow:** entries → normalize (scheme-qualify/narrow/drop) → empty ⇒ loud ValueError → profile gets file:// prohibition appended always + localhost prohibitions & block_ip_addresses under guard → session factory applies.
**Invariant:** normalization must be strictly-narrowing or identity; never widen; set-vs-list semantics preserved through overloads.

## Probe (direct test)
`tests/browser_use/test_browser_use.py` — allowlist normalization matrix (bare host gains http* scheme, www twin added for apex, `????://` narrowed to matched scheme only, file-only rejected, `*.example.com` untouched), localhost-exclusion tests (RFC 6761 label case), kill-after-cancel :450 (suspending kill still completes), failing/timed-out kill retains session :759+. Suite green at HEAD: 47 passed 1 skipped.

## Retrieve
```
search_graph --project pydantic-ai-harness --name-pattern '_normalize_allowed_domain _pattern_allows_localhost _glob_hostname'
```

## Verdict
**Adopt** normalize-at-boundary + strictly-narrowing invariant whenever a third-party matcher's semantics differ from your policy vocabulary. **Adopt** shielded-bounded-swallowed teardown for multi-await external kills. **Omit** www-twin logic if your matcher handles subdomains itself.
