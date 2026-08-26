<!-- capsule-v2 -->
# dbt lineage extraction — how do you recover dependency structure that the SQL grammar cannot even parse?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you extract `{{ ref(...) }}` / `{{ source(...) }}` lineage when Jinja makes the SQL a parse error?

## Model-stem identity + last-string-argument relation rule
**Path/Symbol:** `internal/cbm/extract_dbt.c` (header contract 1–22) + tests tests/test_extraction.c:1907–1960.
**Signature:** (extraction pass) emits per qualifying .sql file: one `Model` definition named by file stem + one usage per ref()/source() call.
**Data Shape:** `ref('x')` → dependency on model x; `ref('pkg','y')` → y (package arg is NOT the relation); `source('group','t')` → t. `{% macro %}` statement blocks deliberately NOT recovered (jinja2 grammar has no statement nodes) rather than approximated.

### Decisive source
```c
// A dbt model is an ordinary .sql file ... dependencies are written
// {{ ref('other_model') }} or {{ source('group', 'table') }} — never as literal
// table names. The SQL grammar cannot read those ...
//   - one Model definition, named by the file stem (dbt's own model identity)
//   - one usage per ref()/source() call, scoped to that Model
/* Both dbt builtins name the relation in their LAST string argument:
 * source('group','table') -> table, and the two-argument
 * ref('package','model') form -> model. */
```

**Flow:** detect dbt-shaped Jinja in `.sql` → mint Model def from stem → walk jinja_expression nodes for fn calls → take LAST string literal as the relation name → emit usages → pass_usages later resolves them into view→table USAGE lineage against Table/View defs.
**Invariant:** Never guess from non-last string args (`raw`, package names are not relations); non-dbt Jinja must produce nothing.
**Probe:** `tests/test_extraction.c:dbt_model_and_ref_lineage` (stg_orders/stg_customers usages), `dbt_source_and_two_arg_ref` (source→customers; no "raw"/"analytics" leakage), `dbt_ignores_non_dbt_jinja`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "ref_lineage", limit: 5 });
```

## Verdict
Adopt stem-identity + last-string-arg extraction for templated SQL lineage; adapt to your template engine; omit macro-definition recovery unless you write a real scanner.
