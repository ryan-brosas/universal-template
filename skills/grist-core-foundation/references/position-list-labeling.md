<!-- capsule-v2 -->
# Position list-labeling — how do mid-list insert positions stay allocable forever with float positions?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** When neighbor-average insertion exhausts float precision, how are existing positions adjusted without ever violating order?

## Order-maintenance for record positions
**Path/Symbol:** `sandbox/grist/relabeling.py:prepare_inserts` (:92-105), `nextfloat/prevfloat` (:130-143), `ListWithAdjustments` (:145-171), fallback `prepare_inserts_dumb` (:50-89), `_group_insertions` (:108-123).
**Signature:** `prepare_inserts(sortedlist, keys) -> ([(index, new_key), ...], [new_key, ...])`.
**Data Shape:** positions are floats ("labels" in list-labeling literature; module header cites Bender/Dietz-Sleator, :14-19); returns adjustments to EXISTING items (order-preserving) plus replacement keys for the inserts.

### Decisive source
```python
# relabeling.py :130-138 — +/- 1 ULP via IEEE bits
def nextfloat(x):
  """
  Returns the next representable float after the float x. ...
  """
  n = struct.unpack('<q', struct.pack('<d', x or 0.0))[0]
  n += (1 if n >= 0 else -1)
  return struct.unpack('<d', struct.pack('<q', n))[0]
# :97-99 — the ordering contract
  The first list contains pairs for existing items in sortedlist that need to be
  adjusted to have new keys (these will not change the ordering). ... To avoid
  reorderings, adjustments should be applied before insertions.
```

**Flow:** batch inserts are grouped per insertion index (`_group_insertions`, sorted by key, ungroup restores caller order) → `ListWithAdjustments` overlays virtual adjustments over the original SortedListWithKey so later decisions see earlier ones without mutating it → each group claims a valid range between neighbors, nudging edges with nextfloat/prevfloat; when no valid range exists the dumb path renumbers 1..N in one pass. Floats were chosen over the paper's integers because JS lacks 64-bit ints (:33-36), giving amortized log(N) relabelings per insert.
**Invariant:** Adjustments MUST be applied before insertions (they preserve order; interleaving can transiently violate it); an adjustment's key must never equal a neighbor's key (hence ULP stepping, never averaging once averages collapse).
**Probe:** `sandbox/grist/test_relabeling.py:test_nextfloat` (:78-100): for sampled magnitudes, `nx > x`, `prevfloat(nx) == x`, and `(nx+x)/2` collapses onto an endpoint — the property that makes ULP-stepping safe; `ItemList.insert_items` (:53-73) shows the apply-adjustments-backwards-by-index recipe.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", mode: "ids", query: "relabeling prepare_inserts nextfloat ListWithAdjustments", limit: 10 });
```

## Verdict
Adopt prepare-inserts returning (adjustments, newKeys) with the apply-first contract and bit-level ULP stepping. Adapt range-finding constants to your density needs. Omit the CONTAINS-free SimpleLookupMapping coupling — this module is pure ordering math with no engine imports beyond sortedcontainers.
