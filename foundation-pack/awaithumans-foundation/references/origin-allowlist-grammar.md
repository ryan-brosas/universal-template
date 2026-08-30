<!-- capsule-v2 -->
# Origin Allowlist Grammar — what does "*.acme.com" match, and which entries are rejected outright?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How must iframe-parent origin parsing and matching behave so a wildcard can never widen past one DNS label?

## Validate-at-parse, match-at-request split
**Path/Symbol:** `packages/python/awaithumans/server/services/embed_token_service.py` — `_LABEL_RE` (:200-205), `_HTTP_ALLOWED_HOSTS` (:205), `InvalidAllowlistEntryError` (:208), `_validate_origin_entry` (:217-299), `_matches_entry` (:302-344), `parse_origin_allowlist` (:347-369), `origin_in_allowlist` (:372-388).
**Signature:** `parse_origin_allowlist(raw: str) -> tuple[str, ...]` (frozen, input order, empty→()`); `origin_in_allowlist(origin, allowlist) -> bool`.
**Data Shape:** entries are scheme+host+port ONLY — path/query/fragment/trailing slash all raise; http allowed only for `localhost`/`127.0.0.1`; ≤1 wildcard, leading label only.

### Decisive source
```python
# Wildcard: entry_host is "*.apex" — strip leading "*.".
apex = entry_host[2:]
suffix = f".{apex}"
if not origin_host.endswith(suffix):     # apex itself does NOT match its own wildcard
    return False
prefix = origin_host[:-len(suffix)]
if not prefix or "." in prefix:          # exactly ONE label below apex
    return False
return bool(_LABEL_RE.match(prefix))
```
Ports compare with scheme defaults substituted for omitted ports (`_default_port`: https→443, else 80); schemes must match exactly.

**Flow:** operator config string → comma-split → strip → skip empties → `_validate_origin_entry` raises on any malformed entry (fail the whole parse, not just the bad entry) → validated tuple stored → at request time `origin_in_allowlist` short-circuits on non-http(s) scheme or missing hostname, then first-match wins.
**Invariant:** `https://*.acme.com` matches `app.acme.com` but NEVER bare `acme.com` nor `a.b.acme.com` — the suffix check plus single-label prefix rule is what keeps a subdomain grant from widening to the apex or to deeper nesting.
**Probe:** `packages/python/tests/embed/test_origin_matching.py` (`test_wildcard_does_not_match_apex`:153, `test_wildcard_does_not_match_two_labels_below_apex`:162, `test_default_port_443_matches_no_explicit_port`:198, `test_reject_entry_with_trailing_slash`:60). Executed behaviorally at pin: apex=False, app.acme=True, two-label=False, :443-equivalence=True.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "origin_in_allowlist _matches_entry parse_origin_allowlist", limit: 5 });
```
Live rank-1..3 line-exact (:302-344, :347-369, :372-388).

## Verdict
Adopt the exact-match/wildcard grammar verbatim including the apex-exclusion and default-port substitution; adapt the localhost-http exception list if your threat model differs; omit IP-literal label skipping only if your operators never enter IPs. Direct tests + behavioral probes green at pin.
