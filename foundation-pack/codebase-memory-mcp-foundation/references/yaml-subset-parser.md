<!-- capsule-v2 -->
# YAML subset parser — when is a hand-rolled YAML parser the right call, and what must it refuse?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What subset covers config needs while staying honest about what it won't parse?

## Key:value + nesting + lists + comments ONLY
**Path/Symbol:** `src/foundation/yaml.h` (contract 1–40) + tests/test_yaml.c:9+.
**Signature:** `cbm_yaml_node_t *cbm_yaml_parse(const char *text, int len);` / `const char *cbm_yaml_get_str(const cbm_yaml_node_t *root, const char *path);`
**Data Shape:** Supports: `key: value` (string/float/bool), indentation-based nested maps, `- item` string lists, `#` comments. Explicitly NOT supported: multiline strings, anchors, flow style. Lookups take dot-separated paths (`http_linker.min_confidence`) with typed getters defaulting on absence.

### Decisive source
```c
/* Handles the subset needed by .cgrconfig:
 *   - key: value pairs (string, float, bool)
 *   - Nested maps (indentation-based)
 *   - String lists (- item)
 *   - Comment lines (#)
 *
 * NOT a general YAML parser — no multiline strings, anchors, flow style, etc. */
```

**Flow:** parse line-wise tracking indent stack → build node tree → path lookups return scalars or caller defaults → free whole tree.
**Invariant:** The refusal list is part of the API contract — inputs relying on unsupported features must fail loudly rather than mis-parse silently.
**Probe:** `tests/test_yaml.c:yaml_parse_null_input`, `yaml_parse_empty_string`, `yaml_parse_negative_len`, `yaml_free_null`; consumer example `.cgrconfig`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_yaml_parse", limit: 5 });
```

## Verdict
Adopt a documented-subset parser only where configs are machine-authored and simple; otherwise use a real YAML lib — the value here is zero-dependency C with an explicit refusal list.
