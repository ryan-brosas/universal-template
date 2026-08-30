<!-- capsule-v2 -->
# Registry resolution ladder — how do you resolve a bare callee name to one qualified node, with confidence you can defend?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What strategy order, confidences, and vetoes make name resolution safe enough to build call graphs from?

## Strategy chain with relation veto and negative caching
**Path/Symbol:** `src/pipeline/registry.c` — confidences (59–70), `cbm_registry_resolve_lineage` (968–981), relation veto (940–949), resolve cache (278–296).
**Signature:** `cbm_resolution_t cbm_registry_resolve(r, callee_name, module_qn, imp_keys[], imp_vals[], imp_count);`
**Data Shape:** Result = {qualified_name, strategy, confidence, status}. Strategies & confidences: `import_map` 0.95 (suffix 0.85), `same_module` 0.90, `unique_name` 0.75, `qualified_suffix` (e.g. 0.x), `suffix_match` 0.55, fuzzy single/multi 0.40/0.30. Bands: high ≥0.7, medium ≥0.45, speculative ≥0.25.

### Decisive source
```c
/* ... table names (users, orders, config) collide with code identifiers across
 * every language, so the DEFAULT resolve never returns them — a veto, not a
 * re-route, so a name-collision does not fall through to a weaker strategy.
 * Every consumer ... is thereby relation-safe by construction. The SQL
 * lineage path opts in via cbm_registry_resolve_lineage. */
if (res.qualified_name && res.qualified_name[0] &&
    cbm_label_is_relation(cbm_registry_label_of(r, res.qualified_name))) {
    res = empty_result();
}
/* Cache the result (including empty — caching the negative answer
 * is just as valuable; same name asks the same question). */
```

**Flow:** exact import_map hit → same-module symbol → unique-name project-wide → qualified-suffix disambiguation (each `App::Alpha::save` routes to its own package) → suffix/fuzzy with import-reachability filtering and caller-proximity preference → cache INCLUDING negatives per TLS table.
**Invariant:** The relation veto applies in the DEFAULT variant only; SQL FROM/JOIN lineage must call the `_lineage` variant — and that variant is deliberately UNCACHED because sharing the cache would poison one variant's semantics with the other's.
**Probe:** `tests/test_registry.c:resolve_same_module`, `resolve_qualified_disambiguates_same_name`, `resolve_unique_name`, `fuzzy_resolve_multiple_best_by_distance`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_registry_resolve_lineage", limit: 5 });
```

## Verdict
Adopt the strategy ladder + numeric bands + negative caching + the two-variant relation split; adapt thresholds if your downstream ranks by them; omit the TLS cache when resolution is rare.
