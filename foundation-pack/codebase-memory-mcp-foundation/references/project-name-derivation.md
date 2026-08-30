<!-- capsule-v2 -->
# Project name derivation — how does an arbitrary repo path become a portable, collision-safe DB filename?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What character mapping keeps derived project names validator-safe without silently erasing CJK paths?

## Safe-set mapping + hex transliteration + FNV-suffixed cap
**Path/Symbol:** `src/pipeline/fqn.c:cbm_project_name_from_path` (416–517) + `fqn_bound_name_len` (385–402).
**Signature:** `char *cbm_project_name_from_path(const char *abs_path);`
**Data Shape:** Legal output charset `[A-Za-z0-9._-]`; separators/unsafe ASCII → `-` (collapsed); each non-ASCII byte → TWO lowercase hex digits; leading `-`/`.` trimmed; consecutive `.` collapsed; empty ⇒ `"root"`; names >200 bytes keep first 191 bytes + `-` + 8-hex FNV-1a of the FULL name.

### Decisive source
```c
/* Non-ASCII bytes ... are NOT dropped to '-' — that silently erased whole path
 * segments and produced unrecognizable / colliding names (#571). Instead each
 * non-ASCII byte is transliterated to its two lowercase hex digits ... */
/* Bound a derived project name to FQN_MAX_NAME_LEN bytes so "<cache>/<name>.db"
 * stays within the filesystem's 255-byte filename-component limit (#624). ...
 * The suffix ends in a hex digit, so the result stays validator-safe. */
/* Otherwise a repo like "/home/u/my project" yields "home-u-my project":
 * indexing creates the DB ... but resolve_store rejects the space and reports
 * project-not-found (#349). */
```

**Flow:** canonicalize via realpath-equivalent (wide-path on Windows for CJK) → normalize separators → map chars per the safe set → collapse runs of `-`/`.` → trim edges → bound to 200 with hash suffix → this name is BOTH the DB filename stem AND the internal `projects.name`, so session detection (`detect_session`) can derive it independently from cwd and find the same DB.
**Invariant:** Indexing-side naming and query-side derivation must be the SAME function or session queries look for a `.db` that doesn't exist.
**Probe:** `tests/test_fqn.c:project_name_*` family (unix/windows/colons/multiple slashes/empty→"root"/mixed separators), plus `tests/test_mcp.c` session-detection coverage near line 10451.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_project_name_from_path", limit: 5 });
```

## Verdict
Adopt safe-set mapping + hex transliteration + bounded-hash suffix for path-derived identifiers; adapt the legal charset to your filesystem/validator; omit root-syntax special-casing if your paths are always real directories.
