<!-- capsule-v2 -->
# Scale-tier contracts — which bugs ONLY reproduce at real-repo scale, and how do you gate them?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you run compiled-binary assertions against large bench repos without slowing every CI run?

## Opt-in binary-driven tier with per-language invariants
**Path/Symbol:** `tests/scale_contract.sh` (header 1–30) + bench repo map.
**Signature:** `bash tests/scale_contract.sh [lang ...]` (default: kotlin java ts; `CBM_SCALE_INCLUDE_C=1` adds the slow C tier; `CBM_BENCH_DIR` overrides repo root).
**Data Shape:** Known scale-only bug classes: Java/TS SIGBUS during parallel extraction on large repos; C function-call attribution landing on the file's Module node instead of the enclosing Function; Kotlin 0 IMPORTS edges (package→module resolution). Runs the COMPILED binary against cbm-bench-validate repos and asserts graph invariants.

### Decisive source
```sh
# Some behavioral bugs only manifest at real-repo scale and cannot be reproduced
# by the small in-process fixtures in tests/test_lang_contract.c ...
# This tier runs the COMPILED binary on the cbm-bench-validate repos and asserts
# invariants at scale. It is SLOW and needs the local bench repos, so it is
# OPT-IN — not part of the fast `scripts/test.sh` unit run.
```

**Flow:** select languages → locate bench repos → invoke installed binary indexing each → assert invariant queries (attribution correctness, edge presence) → exit nonzero lists failures; wired as a separate non-gating-by-default leg so unit CI stays fast.
**Invariant:** Scale tier complements, never replaces, unit contracts; needs external fixtures so must degrade to explicit skip, not silent pass.
**Probe:** the script itself IS the probe (`tests/scale_contract.sh` exit status); companion soak/parallel harnesses in scripts/run-tests-parallel.sh.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "scale_contract", limit: 5 });
```

## Verdict
Adopt an opt-in binary-level scale leg for known scale-only defect classes; adapt bench repos and language list; keep it out of the fast gate by design.
