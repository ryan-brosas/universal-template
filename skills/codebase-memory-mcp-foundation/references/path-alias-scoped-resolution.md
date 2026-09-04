<!-- capsule-v2 -->
# Path alias resolution — how do you turn `@/lib/auth` into something the module-FQN machine can resolve?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What data model lets tsconfig-style aliases plug into import resolution without hard-coding TypeScript?

## Two-step scoped lookup: nearest ancestor scope, longest-prefix alias
**Path/Symbol:** `src/pipeline/path_alias.h` (contract 3–45) + resolver tests tests/test_path_alias.c:91–160.
**Signature:** `char *cbm_path_alias_resolve(const cbm_path_alias_map_t *m, const char *import_path);` (+ `cbm_path_alias_find_for_file`)
**Data Shape:** Alias entry = split prefix/suffix around a single `*` on BOTH key and value (`@/*` → `src/*`); no `*` ⇒ exact match. Maps are sorted by alias_prefix length DESCENDING so `@/lib/*` beats `@/*`. Scopes bind to the directory of their config file; lookup picks the NEAREST ancestor.

### Decisive source
```c
/* Resolves module paths that the indexer would otherwise leave as bare imports
 * (e.g. "@/lib/auth" ...) The data model and resolver below are deliberately
 * language-agnostic so further loaders ... can register additional scopes
 * without touching the resolver or the pipeline. */
/* @/lib/* must beat @/* even though @/* would also match. */
```

**Flow:** load config files (tsconfig/jsconfig compilerOptions.paths + baseUrl) into directory-scoped collections → for an import, find the file's nearest scope → walk aliases longest-prefix-first → splice the wildcard portion into the target → return heap repo-relative path or NULL.
**Invariant:** Longest-prefix ordering is semantic, not cosmetic; extension stripping and exact matches are distinct paths; loader additions must not touch the resolver.
**Probe:** `tests/test_path_alias.c:path_alias_at_wildcard`, `path_alias_specificity_longest_first`, `path_alias_exact_match`, `path_alias_strips_ext`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_path_alias_resolve", limit: 5 });
```

## Verdict
Adopt the pluggable scoped-alias model for any bundler-config import rewriting; adapt loaders per ecosystem; keep the resolver pure — new sources register scopes only.
