<!-- capsule-v2 -->
# Client-side validation helpers — how do shared field guards produce named errors instead of TypeErrors?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** What is the shared validation vocabulary, and why do timing and metadata finiteness rules deliberately differ?

## _validation.py
**Path/Symbol:** `ingestion/src/zep_ingest/_validation.py:16` (`_first_non_finite`), `:31` (`_is_finite_number`), `:53` (`is_scalar_or_scalar_array`), `:94` (`check_timestamp`), `:116` (`check_scalar_map`), `:162` (`require_int_range`), `:177` (`require_nonnegative_number`).
**Signature:** All append to a passed `errors: list[str]` (check_*) or raise ConfigurationError immediately (require_*); SCALARS = (str,int,float,bool,NoneType).
**Data Shape:** Metadata/attributes values: scalar OR array of scalars; empty arrays and None elements refused; nested refused.

### Decisive source
```python
# _is_finite_number docstring — the asymmetry is NOT an oversight:
# Deliberately NOT used by the metadata guards ... JSON integers are
# arbitrary-precision, so ``10**400`` in a metadata value serializes and
# reparses exactly. What those guards reject is NaN/Infinity, which have no
# JSON form at all. Here [timing] the constraint is the opposite one — not
# "can this be written as JSON" but "can the C clock take it" — so it is a
# float's range that binds.
try:
    return math.isfinite(value)
except OverflowError:
    return False

# require_nonnegative_number — why finiteness is part of the contract:
# a non-finite timeout silently stops being a timeout — ``elapsed >= nan``
# and ``elapsed >= inf`` are never true, so the poll loop never gives up.
```

**Flow:** dataclasses call check_* per field collecting ALL errors into one ConfigurationError ("Invalid episode: …; …"); public numeric config goes through require_int_range (bool is not an int here) / require_nonnegative_number. check_timestamp demands RFC3339 WITH timezone offset; epoch numbers from JSONL get a named error instead of AttributeError.
**Invariant:** Two different finiteness regimes: JSON-shape guards reject only non-finite FLOATS (ints are arbitrary-precision and fine); duration/rate guards reject huge ints too because time.sleep/monotonic overflow. A porter who unifies them either rejects valid metadata or crashes on 10**400 timeouts.
**Probe:** `grep -c 'def test' ingestion/tests/test_types.py ingestion/tests/test_sequential_submitter.py | awk -F: '{s+=$2} END{print s}'` → ≥52 incl. `test_int_too_large_for_a_float_refused`, `test_non_finite_min_interval_refused`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "check_scalar_map require_nonnegative finite validation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt collect-all-errors check_* + dual finiteness regimes + bool-is-not-int config guards; adapt limits to your API contract; omit Zep error wording.
