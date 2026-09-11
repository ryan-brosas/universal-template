<!-- capsule-v2 -->
# Dump verify floors — how do you prove an imported graph isn't silently truncated?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What ratio/floor checks distinguish a legitimate sparse dump from a broken one?

## Sparse-floor + shortfall-ratio verification
**Path/Symbol:** `src/foundation/dump_verify.{h,c}` + tests/test_dump_verify.c:14–30 (`dump_verify_no_baseline`, `dump_verify_sparse_at_floor`, `dump_verify_shortfall_below_ratio`).
**Signature:** verify(dump_count, baseline_count, floor, ratio) → pass/fail per rule.
**Data Shape:** No baseline ⇒ accept unconditionally (nothing to compare). Sparse dumps accepted only AT/ABOVE the configured floor; counts below baseline by more than the allowed shortfall ratio fail.

### Decisive source
```c
TEST(dump_verify_no_baseline) { ... }        /* nothing to compare -> OK */
TEST(dump_verify_sparse_at_floor) { ... }    /* sparse but >= floor -> OK */
TEST(dump_verify_shortfall_below_ratio) { ... } /* missing too much -> FAIL */
```

**Flow:** capture baseline node/edge counts (previous generation or manifest) → after dump/import compute new counts → apply rules in order: no-baseline pass, floor pass, ratio check → failure blocks publication/import with a typed error.
**Invariant:** Floors and ratios must BOTH be configurable — absolute floors alone break small repos; ratios alone break huge ones. Order matters: cheapest, most decisive checks first.
**Probe:** the three named tests plus IO-side twins in tests/test_dump_verify_io.c.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "dump_verify", limit: 5 });
```

## Verdict
Adopt tiered count verification for any pipeline whose output feeds downstream tools; adapt thresholds; pair with the artifact size-mismatch gate for full coverage.
