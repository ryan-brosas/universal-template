<!-- capsule-v2 -->
# DependencyGraph arena-interned import graph with basename duality — why do reverse-edge removals happen eagerly while forward keys linger, and when must basename matching be refused?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** How does an O(1) imported-by lookup coexist with ambiguous same-basename modules?

## Forward list + reverse set + interned string arena
**Path/Symbol:** `src/explore.zig:DependencyGraph` :300–642 (`internString` :328, `setDeps` :354, `remove` :389, `getImportedByFiltered` :426, `getTransitiveDependents` :471, `getTransitiveBounded` :568).
**Data Shape:** `forward: path → ArrayList(deps)`; `reverse: dep → StringHashMap(void dependents)`; `str_arena` + `interned: resolved → arena copy` — graph-MINTED strings (relative imports normalized to repo paths) are interned so watcher re-indexing reuses one copy instead of growing the arena per import.

### Decisive source
```zig
// Basename fallback (imports often use short names). Skipped when the basename
// is ambiguous across indexed files (allow_basename=false): a bare `import conf`
// can't be attributed to a specific same-basename file (a/conf.py vs b/conf.py).
if (allow_basename and !std.mem.eql(u8, path, basename)) { ... merge reverse[basename] ... }
```
Removal asymmetry:
```zig
pub fn remove(self: *DependencyGraph, path: []const u8) void {
    // Remove forward edges and their reverse counterparts ... [eagerly]
    // We should NOT remove reverse[path] here — other files still reference
    // `path` in their forward edges. The reverse entry is cleaned up lazily
    // when those files are re-indexed or removed.
```
Bounded traversal for docs (`getTransitiveBounded`) carries BOTH a depth cap AND a result cap — the import graph's "historically unbounded helpers" caused runaway walks.

**Flow:** parser emits raw imports per file → resolveDependencyKey normalizes (relative-import resolution, dart/python/ocaml/res-specific shims) → internString → setDeps swaps the forward list while surgically removing stale reverse entries (empty reverse sets are fetched-removed and deinited) → queries: exact reverse hit first, optional basename fallback merged dedup, BFS variants forward/backward with cycle safety (visited set) and depth caps.
**Invariant:** Reverse index must ALWAYS reflect current forward edges of CHANGED files only; never delete reverse[path] on remove(path) (importers still point at it). Cycles cannot hang BFS because visited marks enqueue-time. The transitive-dependents walk enqueues basename KEYS as pseudo-nodes too (visited covers both forms) — dropping that splits the traversal.
**Probe:** `src/test_explore.zig` :1474 "dep-graph: remove cleans forward and reverse edges", :1502 "dep-graph: cycle does not cause infinite BFS", "dep-graph: reverse index gives O(1) imported_by lookup", "dep-graph: transitive dependencies (forward BFS)", Explorer integration pair ("Explorer integration — getImportedBy uses reverse index"); `src/test_parser.zig` "audit: ambiguous bare import must not cross same-basename dirs".
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", name_pattern: "getImportedByFiltered", limit: 10 });
```

## Verdict
Adopt the dual-index shape with eager-reverse/lazy-forward-key cleanup and the ambiguity gate on basename matching; adapt import-resolution shims per language; omit markdown link-graph twin (markdown_graph.zig) unless porting doc navigation.
