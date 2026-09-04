<!-- capsule-v2 -->
# Badge signature scheme — 8-char HMAC URLs, late-mode suffix grammar, and SVG width math without a font

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How do badge URLs stay unguessable, cache-hostile, and embeddable in READMEs — including the "-2" suffix that silently changes status semantics?

## hc/lib/badges + views.badge / check_badge
**Path/Symbol:** `hc/lib/badges.py:check_signature` (:103-106), `get_badge_url` (:108-117), `get_badge_svg` (:88-100), WIDTHS/COLORS tables; views `hc/api/views.py:badge` (:727-778), `check_badge` (:781-811); URL converters `hc/api/urls.py:QuoteConverter/SHA1Converter`.
**Signature:** `check_signature(badge_key: str, tag: str, sig: str) -> bool`; `get_badge_url(badge_key, tag, fmt="svg", with_late=False) -> str`; view dispatch on `len(signature) == 10 and endswith("-2")`.
**Data Shape:** sig = base64_hmac(badge_key-as-salt, tag, SECRET_KEY, sha1)[:8] (+ "-2" when NOT with_late). fmt ∈ svg|json|shields. COLORS: up #4c1, late #fe7d37, down #e05d44; shields map success/important/critical.

### Decisive source
```python
# hc/lib/badges.py — the whole auth is a truncated HMAC over (key, tag)
def check_signature(badge_key, tag, sig):
    ours = base64_hmac(str(badge_key), tag, settings.SECRET_KEY, algorithm="sha1")
    return ours[:8] == sig[:8]        # compare FIRST 8 chars of BOTH — suffix ignored

# hc/api/views.py — "-2" flips grace reporting to plain up
with_late = True
if len(signature) == 10 and signature.endswith("-2"):
    with_late = False
...
elif check_status == "grace":
    grace += 1
    if status == "up" and with_late:
        status = "late"
if fmt == "svg":
    # For SVG badges, we can leave the loop as soon as we
    # find the first "down"
    break
```

**Flow:** get_badge_url builds the canonical URL per (target, format, late-mode). View: validate fmt → parse with_late from signature shape → check_signature → iterate project's checks filtered by tag (`tags__contains=tag` approximation then precise tags_list() match) accumulating total/grace/down; early-exit only in svg mode once "down" is certain. json returns {status,total,grace,down}; shields wraps schemaVersion-1 JSON. Tag URLs quote special characters via the custom "quoted" path converter (db@dc1 → db%2540dc1 round-trip).
**Invariant:** The signature binds key+tag but NOT format or late-mode: "-2" must be syntactically distinguishable yet verify against the same 8-char prefix — hence comparing ours[:8] to sig[:8] rather than equality; a porter who "fixes" this to full-string comparison breaks every -2 URL. Late mode exists because GitHub README badges render stale grace as failure visually; default (no -2) treats grace as "late" ONLY when overall still up. @never_cache + Access-Control-Allow-Origin:* are contract features (README <img> embedding), not boilerplate.
**Probe:** `hc/api/tests/test_badge.py::test_late_mode_returns_late_status` vs `test_it_treats_late_as_up`, `test_it_handles_special_characters`, `test_it_rejects_bad_signature` (404), `hc/lib/tests/test_badges.py::test_get_width_works`, plus shields assert :80-90.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "badge signature hmac svg shields", limit: 10 });
```
Resolves line-exact: check_signature :103-106 and test pins test_badge.py :28-97.

## Verdict
Adopt truncated-HMAC URL signatures with semantic suffixes compared away by the [:8] slice, per-format response projection, and never-cache+CORS headers for embed surfaces. Adapt color tokens, shields endpoint wrapping, and width table (or swap for real text measurement). Omit the QuoteConverter if your framework already round-trips encoded path segments.
