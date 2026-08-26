<!-- capsule-v2 -->
# Label allowlist drift guards — how do you keep a C predicate and an SQL fragment from disagreeing?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** When the same vocabulary exists in C code and inline SQL strings, what test keeps them in lockstep?

## Bidirectional membership assertions between predicate and SQL literal
**Path/Symbol:** tests/test_store_nodes.c:28 (`sql_label_allowlists_match_cbm_label_is_type_like`), 59 (`sql_relation_labels_match_cbm_label_is_relation`).
**Signature:** `bool cbm_label_is_type_like(const char *label);` vs `#define CBM_SQL_TYPE_LIKE_LABELS "'Class','Struct',..."`.
**Data Shape:** Type-like = {Class, Struct, Interface, Enum, Type, Trait}; relation = {Table, View} (registry symbols but NOT type-like — resolve vetoes them so identifiers never bind into lineage). Callable-or-type adds exactly Function+Method.

### Decisive source
```c
for (size_t i = 0; i < ...; i++) {
    ASSERT_TRUE(cbm_label_is_type_like(type_like[i]));
    char quoted[64];
    snprintf(quoted, sizeof(quoted), "'%s'", type_like[i]);
    ASSERT_NOT_NULL(strstr(CBM_SQL_TYPE_LIKE_LABELS, quoted));
}
/* And nothing the predicate rejects may be smuggled into the type-like
 * fragment — otherwise the SQL would widen past the C contract. */
ASSERT_FALSE(cbm_label_is_type_like(not_type_like[i]));
ASSERT_NULL(strstr(CBM_SQL_TYPE_LIKE_LABELS, quoted));
```

**Flow:** every accepted label must appear quoted in the SQL fragment AND every rejected label must be ABSENT — both directions checked, so drift in either artifact fails.
**Invariant:** Dual representations of one vocabulary are a defect factory; the guard converts silent widening/narrowing into test failures.
**Probe:** the two named tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_label_is_type_like", limit: 5 });
```

## Verdict
Adopt bidirectional vocabulary-consistency tests wherever logic exists twice (C + SQL, or two languages); adapt label sets; the negative-direction assertion is the half everyone forgets.
