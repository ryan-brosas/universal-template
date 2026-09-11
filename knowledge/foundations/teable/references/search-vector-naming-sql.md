<!-- capsule-v2 -->
# Search-vector naming & SQL generation — how does teable build deterministic managed-object names and the generated-column expression so a rebuild is idempotent and collision-free?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** The generated column name, index name, candidate key, and the STORED expression must be deterministic from the field set so re-analysis converges and rebuilds drop the same objects. How are they derived, and how is the substring document built?

## stableHash-derived names + lower(coalesce(..) || '\n' || ..) document expression
**Path/Symbol:** `packages/v2/adapter-table-query-ops-postgres/src/searchVector.ts` — `buildSearchVectorNames` (1650–1665), `buildScopedExpressionIndexNames` (1667–1682), `buildSearchDocumentExpression` (1684–1689), `buildSearchDocumentExpressionWithAlias` (1691–1702), `buildSearchDocumentDefinitionMarker` (2354–2362), `qualifyOperatorClass` (2364–2371), `stableHash` (2893–2899), `quoteLiteral` (2888), `escapeLikeWildcards` (2890–2891), `normalizeLanguageConfig` (1636–1640), `lengthBucket` (1642–1648).
**Signature:** `buildSearchVectorNames(tableId, providerCapability, fields) => {candidateKey, generatedColumnName, indexName}`.
**Data Shape:** hash = `stableHash(\`${tableId}:substring:${provider}:${operatorClass}:${fields.map(f=>`${f.fieldId}=${f.fieldDbName??''}`).join(',')}\`)` (8-hex, `(hash*31+charCode)>>>0`); candidateKey = `search_document:${tableId}:${provider}:${hash}`; column = `__tqops_search_${hash}`.slice(0,63); index = `idx_tqops_search_${tableId}_${hash}`.slice(0,63). Scoped variant sorts the field list before hashing and uses `scoped_search_expression:${tableId}:${hash}` / `idx_tqops_search_scope_${tableId}_${hash}`.

### Decisive source
```ts
const buildSearchDocumentExpression = (fieldDbNames) => {
  const document = fieldDbNames.map(f => `coalesce(${quoteIdentifier(f)}::text, '')`).join(` || E'\\n' || `);
  return `lower(${document || quoteLiteral('')})`;
};
// definition marker stored in the COMMENT so inventory can detect expression drift:
const buildSearchDocumentDefinitionMarker = (expression, cap) =>
  `teable.table-query-ops.search-document:${SEARCH_DOCUMENT_DEFINITION_VERSION /* v1 */}:${stableHash(`${expression}:${cap.provider}:${cap.operatorClass}:${cap.operatorClassSchema ?? ''}`)}`;
// LIKE wildcard escaping so a probe can't inject % or _:
const escapeLikeWildcards = (input) => input.replace(/\\/g,'\\\\').replace(/%/g,'\\%').replace(/_/g,'\\_');
// language config is whitelisted to word/dot chars, else 'simple':
if (!/^[\w.]+$/.test(trimmed)) return DEFAULT_LANGUAGE_CONFIG; // 'simple'
```

**Flow:** names are derived from a stable hash over tableId+provider+operatorClass+the ordered field list (scoped variant sorts first) → the generated column is `lower()` of each field `coalesce(...::text,'')` joined by `E'\n'` → the expression is stamped into a COMMENT marker (versioned + hashed) so inventory can detect a drift in the field set or provider → operator class is schema-qualified when a non-default schema is present → LIKE probes escape `\ % _` before interpolation.
**Invariant:** names are deterministic and length-capped at 63 (Postgres identifier limit) so re-analysis converges to the same objects and rebuilds drop exactly what was created; the expression is always `lower()` of newline-joined `coalesce(...,'')` casts so nulls and mixed case are normalized; the definition marker version+hash is what makes a changed field set detectable as `generated_expression_mismatch`.
**Probe:** `searchVector.spec.ts` exercises `addSearchSemanticsBaselineDeltas`/`chooseScopedExpressionNextAction`/`selectSubstringSearchProvider`; the naming/expression helpers are pinned by the lifecycle DB spec (create→inspect→rebuild asserts the same names round-trip).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildSearchVectorNames buildSearchDocumentExpression buildSearchDocumentDefinitionMarker stableHash", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt deterministic stable-hash naming with 63-char caps, the newline-joined lower(coalesce) document expression, the versioned definition-marker COMMENT, and LIKE wildcard escaping; adapt hash seed, prefixes, and marker namespace to host; omit teable's substring provider/operator-class coupling if the host uses another access method. Coverage: fully indexed (no parse_partial in cited ranges).
