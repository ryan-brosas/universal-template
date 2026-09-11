<!-- capsule-v2 -->
# Header validity & case-insensitivity — what characters may header names/values contain, and how does CaseInsensitiveDict preserve insertion order?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** What regex gates check_header_validity, and what storage design makes CaseInsensitiveDict both case-insensitive AND order/case-preserving?

## utils.check_header_validity / structures.CaseInsensitiveDict
**Path/Symbol:** `src/requests/utils.py:check_header_validity` (:1087-1119), validators imported from `_internal_utils` (HEADER_VALIDATORS); `src/requests/structures.py:CaseInsensitiveDict` (:20-93).
**Signature:** `check_header_validity(header: tuple[name, value]) -> None`; `CaseInsensitiveDict(MutableMapping[str, _VT])`.

### Decisive source
```python
def __setitem__(self, key, value):
    # Use the lowercased key for lookups, but store the actual
    # key alongside the value.
    self._store[key.lower()] = (key, value)
def __getitem__(self, key):
    return self._store[key.lower()][1]
def lower_items(self):
    return ((lowerkey, keyval[1]) for (lowerkey, keyval) in self._store.items())
def copy(self):
    return CaseInsensitiveDict(self._store.values())     # re-inserts with ORIGINAL casing

# _internal_utils.py:
_HEADER_VALIDATORS_STR = [_check_header_name_str, _check_header_value_str]
def _validate_header_part(header, header_part, header_validator_index):
    if isinstance(header_part, str): validator = ...
    elif isinstance(header_part, bytes): validator = ...
    else:
        raise InvalidHeader(f"Header part ({header_part!r}) ... must be of type str or bytes")
    if not validator.match(header_part):
        raise InvalidHeader(f"Invalid leading whitespace, reserved character(s), "
                            f"or return character(s) in header {kind}: {header_part!r}")
```

**Flow:** every header passes name+value regex validation at PREPARE time (rejecting leading whitespace, CR/LF injection chars — non-str/byte types rejected loudly) → stored into CID where lowercase key indexes `(originalKey, value)` tuples → iteration yields LAST-SET casing in insertion order; lookups/deletes case-folded → equality compares via lower_items maps both ways.
**Invariant:** The store-of-tuples trick preserves wire-format header casing (some servers care) while giving dict-grade O(1) case-insensitive ops; `copy()` round-trips through values so original keys survive copies but duplicate-cased keys collapse silently (last wins — documented undefined behavior when equal-lowercase keys collide in constructor/update). Validators live in one module consumed by BOTH requests and urllib3-side checks — port them as a pair.
**Probe:** Direct tests: `tests/test_requests.py::test_header_validation` (:1789, InvalidHeader on bad name/value chars), `::test_headers_preserve_order` (:504), `::test_header_remove_is_case_insensitive` (:1757); unit level `tests/test_structures.py::TestCaseInsensitiveDict`. `grep -n "key.lower()" src/requests/structures.py` → 3 hits (:62/:65/:68).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "CaseInsensitiveDict lower_items store", limit: 10 });
```

## Verdict
Adopt tuple-store CID wholesale (it's the canonical pattern) and prepare-time validation. Adapt validator regexes to host RFC profile. Omit py2 LookupDict attr magic unless porting status_codes too.
