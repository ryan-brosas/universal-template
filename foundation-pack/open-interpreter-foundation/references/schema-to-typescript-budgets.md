<!-- capsule-v2 -->
# schema-to-typescript-budgets — how are untrusted JSON Schemas rendered into finite TS declarations?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** How does a hostile/recursive tool schema become a bounded `declare const tools: {...}` line?

## Budget constants and failure mode
**Path/Symbol:** `codex-rs/code-mode-protocol/src/json_schema_types.rs` : constants (:8-16), `render_json_schema_to_typescript` (:18-25).
**Data Shape:** `MAX_LOCAL_REF_EXPANSIONS_PER_PATH = 2`, `MAX_TOTAL_LOCAL_REF_EXPANSIONS = 32`, `MAX_RENDERED_SCHEMA_BYTES = 16_000`, `MAX_RENDER_WORK_BYTES = 64_000`; every exhaustion path degrades to `"unknown"`, never an error.

### Decisive source
```rust
// Expose one nested recursive shape, then fall back to `unknown` on the next
// occurrence so generated tool declarations remain finite.
const MAX_LOCAL_REF_EXPANSIONS_PER_PATH: usize = 2;
// Charge intermediate render strings as they are built so repeated local refs
// cannot allocate unbounded expanded copies before the final schema cap runs.
const MAX_RENDER_WORK_BYTES: usize = MAX_RENDERED_SCHEMA_BYTES * 4;
```

**Flow:** $ref resolution tracks per-pointer ACTIVE expansions (a path may recurse twice then yields `unknown`) + a global 32-expansion budget; nested `$id` objects start NEW schema resources where fragment refs DON'T resolve (depth > 0 → unknown); render work is metered per literal/line/property against a byte budget that is spent as intermediate strings build — not checked once at the end.
**Invariant:** The work-byte budget is the DoS defense: checking only the final size would let one iteration allocate gigabytes before the check. allOf branches parenthesize union members (`parenthesize_union_for_intersection`); property descriptions become `// comment` lines only when ANY sibling has one; properties are sorted for determinism. `$ref` siblings (non-$ref/$defs keys) intersect via `(ref) & (siblings)` unless either side is unknown.
**Probe:** in-file tests at pin (`json_schema_types_tests.rs`, 200 lines) incl. the `Result~1item~0v1` percent-encoded pointer case pinned through `augment_tool_definition`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "render_json_schema_to_typescript MAX_LOCAL_REF_EXPANSIONS_PER_PATH", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-budget ladder, active-expansion map, nested-$id scoping, and degrade-to-unknown policy verbatim (security-relevant). Adapt the emitted syntax. Direct tests exist in-file.
