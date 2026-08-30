<!-- capsule-v2 -->
# URI requoting ladder — why unquote-unreserved then quote-with-percent-safe, and what's the fallback?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** How does requote_uri produce consistently-quoted URLs without double-encoding existing percent-escapes?

## utils.unquote_unreserved / requote_uri
**Path/Symbol:** `src/requests/utils.py:unquote_unreserved` (:680-701), `.requote_uri` (:704-723), UNRESERVED_SET (:675-677).
**Signature:** `unquote_unreserved(uri: str) -> str`; `requote_uri(uri: str) -> str`.

### Decisive source
```python
UNRESERVED_SET = frozenset("ABC...XYZabc...xyz0123456789-._~")   # RFC 3986 unreserved

parts = uri.split("%")
for i in range(1, len(parts)):
    h = parts[i][0:2]
    if len(h) == 2 and h.isalnum():
        try:
            c = chr(int(h, 16))
        except ValueError:
            raise InvalidURL(f"Invalid percent-escape sequence: '{h}'")
        if c in UNRESERVED_SET:
            parts[i] = c + parts[i][2:]     # decode %41 -> A
        else:
            parts[i] = f"%{parts[i]}"       # keep reserved escapes encoded
    else:
        parts[i] = f"%{parts[i]}"           # malformed → literal % preserved
return "".join(parts)

# requote_uri:
try:
    return quote(unquote_unreserved(uri), safe="!#$%&'()*+,/:;=?@[]~")
except InvalidURL:
    # couldn't unquote → quote raw but keep '%' safe so stray percents survive
    return quote(uri, safe="!#$&'()*+,/:;=?@[]~")
```

**Flow:** split-on-% scan decodes ONLY hex escapes mapping into RFC 3986 unreserved set (`%41`→`A`); reserved/unknown escapes (`%20`) stay encoded; malformed hex raises InvalidURL → requote_uri's PRIMARY path quotes the normalized URI with `%` KEPT safe (existing valid escapes pass through untouched) → on InvalidURL (bare `%` present) the FALLBACK path drops `%` from the safe list so quote() encodes stray percents into `%25` while preserving all other reserved delimiters.
**Invariant:** The two safe-lists differ by exactly one char (`%`) — that single-char difference IS both the double-encode prevention (primary keeps `%`) and the bare-percent repair (fallback encodes it). Porters who unify the lists either double-encode valid escapes or crash on bare-percent input. Split-based scanning avoids regex backtracking blowups on adversarial URIs.
**Probe:** Direct tests: `tests/test_utils.py::test_requote_uri_with_unquoted_percents` (:491, parametrized incl. bare-`%ppicture`→`%25ppicture` case) + `test_get_auth_from_url` region above it; `grep -c 'safe_with' src/requests/utils.py` → 4 lines (2 defs + 2 uses).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "unquote_unreserved requote percent", limit: 10 });
```

## Verdict
Adopt the two-safe-list ladder verbatim. Adapt quote() to host's percent-encoding util keeping safe-list semantics. Omit nothing.
