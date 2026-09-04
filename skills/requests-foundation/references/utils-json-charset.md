<!-- capsule-v2 -->
# JSON charset detection — how does guess_json_utf pick utf-8/16/32 from four bytes?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** What byte patterns identify each JSON-permitted encoding in Response.json's decode path?

## utils.guess_json_utf
**Path/Symbol:** `src/requests/utils.py:guess_json_utf` (:1008-1037) with `_null/_null2/_null3` sentinels (:1002-1005).
**Signature:** `guess_json_utf(data: bytes) -> str | None`.
**Data Shape:** Inspects only `data[:4]`; returns one of {"utf-32","utf-8-sig","utf-16","utf-8","utf-16-be","utf-16-le","utf-32-be","utf-32-le"} or None.

### Decisive source
```python
sample = data[:4]
if sample in (codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE):
    return "utf-32"          # BOM included — decoder must strip
if sample[:3] == codecs.BOM_UTF8:
    return "utf-8-sig"       # MS-style BOM, discouraged but honored
if sample[:2] in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE):
    return "utf-16"
nullcount = sample.count(_null)
if nullcount == 0:
    return "utf-8"
if nullcount == 2:
    if sample[::2] == _null2: return "utf-16-be"   # 1st+3rd bytes null
    if sample[1::2] == _null2: return "utf-16-le"  # 2nd+4th bytes null
if nullcount == 3:
    if sample[:3] == _null3: return "utf-32-be"
    if sample[1:] == _null3: return "utf-32-le"
return None                 # undetectable → caller falls back to .text path
```

**Flow:** BOM checks first (full-BOM utf-32 needs all 4 bytes compared) then null-position heuristics on the ASCII JSON prefix (RFC 4627 §3 guarantees first chars are ASCII so nulls mark UTF width/endian).
**Invariant:** The BOM-vs-heuristic split matters: `"utf-8-sig"` (not plain utf-8) so the decoder strips the BOM; utf-16/32 WITH BOM return generic names because Python decoders consume BOMs, but WITHOUT BOM they need explicit BE/LE. A porter who returns None on BOM inputs double-decodes BOM bytes as text.
**Probe:** Direct tests: `tests/test_utils.py` guess_json_utf parametrized `test_encoded` ×8 encodings (:422) + `test_bad_utf_like_encoding` (:426, all-null returns None); `grep -n "nullcount == 2" src/requests/utils.py` → 1 hit (:1025).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "guess_json_utf BOM null count", limit: 10 });
```

## Verdict
Adopt detection order verbatim. Adapt to host codec registry keeping -sig distinction. Omit nothing; function is dependency-free.
