<!-- capsule-v2 -->
# Allocator binding order — why does your whole program's allocator choice hinge on the FIRST statement of main?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you route tree-sitter and SQLite allocations into your custom allocator without silent no-ops?

## Bind-before-initialize with idempotent re-assert
**Path/Symbol:** `internal/cbm/cbm.c:cbm_alloc_init` (315–350) + defense-in-depth re-assert in `cbm_init` (355–365); called as the very first statement of `main` (`src/main.c:2427`).
**Signature:** `void cbm_alloc_init(void);` → `ts_set_allocator(cbm_ts_malloc, cbm_ts_calloc, cbm_ts_realloc, cbm_ts_free)` and `sqlite3_config(SQLITE_CONFIG_MALLOC, &cbm_sqlite_mem)`.
**Data Shape:** Prod builds define `CBM_BIND_TS_ALLOCATOR=1`; test/ASan builds deliberately use CRT so binding would create an alloc/free mismatch.

### Decisive source
```c
/* sqlite3. SQLITE_CONFIG_MALLOC MUST run before sqlite3_initialize / the
 * first sqlite3_open* — otherwise sqlite3_config returns SQLITE_MISUSE
 * silently and the binding is ignored. cbm_alloc_init() runs as the very
 * first statement of main(), before cbm_mcp_server_new → cbm_store_open*. */
int sqlite_rc = sqlite3_config(SQLITE_CONFIG_MALLOC, &cbm_sqlite_mem);
assert(sqlite_rc == SQLITE_OK && "SQLITE_CONFIG_MALLOC must run before sqlite3_initialize");
...
/* Defense-in-depth allocator binds (idempotent). main() calls cbm_alloc_init
 * first; this covers non-main entry points (pipeline passes call cbm_init). */
```

**Flow:** process entry → cbm_alloc_install (tree-sitter ts_set_allocator + SQLITE_CONFIG_MALLOC) → everything downstream (parsers, stores) allocates through mimalloc → non-main entry points (tests, pipeline passes) re-assert idempotently via cbm_init.
**Invariant:** A late bind is a SILENT failure — the assert is the only guard; never allocate through SQLite or tree-sitter before binding; sanitizer builds must NOT bind (mismatch).
**Probe:** `tests/test_stack_overflow.c:ts_allocator_bound_to_mimalloc_issue424` plus the mimalloc wrap flags for Linux measurement in Makefile.cbm (LDFLAGS_TEST MIMALLOC_WRAP_FLAGS_POSIX).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_alloc_init", limit: 5 });
```

## Verdict
Adopt bind-first + assert + idempotent re-assert whenever embedding libraries with pluggable allocators; adapt which libraries you bind; omit Windows --wrap redirection unless you must measure allocations there too.
