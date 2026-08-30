<!-- capsule-v2 -->
# Sanitizer-awareness header — why do sanitizer builds silently break timing budgets, and what's the one-spelling fix?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How should code ask "am I instrumented?" when compilers disagree about announcing it?

## Build-define source of truth + per-sanitizer compiler probes
**Path/Symbol:** `src/foundation/sanitized.h` (whole header is the contract).
**Signature:** (macro predicate) "is this binary instrumented?" — one spelling for ASan/UBSan/TSan/MSan detection.
**Data Shape:** Two deliberate sources: `CBM_SANITIZED_BUILD` set by the build system — the ONLY source that can answer for UBSan/trap-UBSan (undefined-behavior instrumentation leaves no macro and no __has_feature bit) — plus clang/GCC `__has_feature`/`__SANITIZE_*__` probes as backstop.

### Decisive source
```c
/* ... four sites, four spellings, one of which (the C# LSP bench) only
 * recognised ASan and therefore ran a NATIVE 200ms budget on a
 * ThreadSanitizer binary. Ask it here instead.
 * ...
 * That is not hypothetical: CFLAGS_TSAN never included SANITIZED_DEFINE (it keys
 * off $(SANITIZE), which TSan does not use), so every sanitized budget compiled
 * to its native value on the one leg they were written for, and
 * subprocess_run_spawn_failure failed on the very PR meant to fix it.
 * Both clang and GCC spellings are listed because they disagree ... */
```

**Flow:** build system defines CBM_SANITIZED_BUILD on sanitized legs → every timing budget/retry window/stack floor consults the single predicate → widened budgets apply uniformly across sanitizers → a probe firing without the define logs rather than #error (correct-but-flagged beats broken).
**Invariant:** Never key budgets off `$(SANITIZE)` alone; never let per-site conditions multiply — the header exists because four divergent spellings already shipped a native-budget-on-TSan bug.
**Probe:** consumed by the TSan leg (`make test-tsan`, Makefile.cbm TEST_TSAN_SUITES) and by subprocess timeout tests that fail under wrong budgets; see tests/test_stack_overflow.c crash-safety family which runs on sanitized lanes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "sanitized", limit: 5 });
```

## Verdict
Adopt one-predicate instrumented-detection with build-system primacy; adapt the probe list to your compilers; the no-#error posture is optional but recommended.
