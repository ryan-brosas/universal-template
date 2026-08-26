<!-- capsule-v2 -->
# TESTS edge derivation — how do you know which tests cover which production functions without any test framework integration?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What naming-convention heuristics create TESTS and TESTS_FILE edges from ordinary CALLS data?

## is_test source + non-test target ⇒ TESTS; file twins via suffix map
**Path/Symbol:** `src/pipeline/pass_tests.c:cbm_pipeline_pass_tests` (285+) with header contract (1–20).
**Signature:** `int cbm_pipeline_pass_tests(cbm_pipeline_ctx_t *ctx, const cbm_file_info_t *files, int file_count);`
**Data Shape:** Runs AFTER pass_calls. Function testness from convention prefixes/suffixes per language (`Test` Go methods, `test_` pytest, `_test.go` files, `.spec.ts`/`.test.ts`, `describe_/context_`). TESTS_FILE pairs production File nodes via suffix rewriting (`_test.go`→`.go`, `test_service.py`→`service.py`, `service.test.ts`→`service.ts`).

### Decisive source
```c
/* Scans CALLS edges in the graph buffer: if the source function has
 * is_test=true and the target does not, creates a TESTS edge.
 * Also creates TESTS_FILE edges from test File nodes to the production
 * File nodes they correspond to (naming convention: _test.go → .go, etc.)
 * Depends on: pass_calls having populated CALLS edges */
```

**Flow:** walk CALLS edges → classify source/target testness → cross-boundary calls (test→production) emit TESTS edges → derive file-level twins by stripping language-specific test markers from paths → emit TESTS_FILE.
**Invariant:** Direction is strictly test→production; conventions are per-language tables, never a global regex; pass ordering after CALLS is mandatory.
**Probe:** `tests/test_edge_structural.c:es_tests_crossfile_python`, `es_tests_crossfile_typescript`; registry-scale guard noted in tests/test_registry.c:863.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_pipeline_pass_tests", limit: 5 });
```

## Verdict
Adopt convention-driven test linkage when framework hooks are unavailable; adapt the marker table; omit TESTS_FILE if you only need symbol-level coverage.
