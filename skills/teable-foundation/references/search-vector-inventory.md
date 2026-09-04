<!-- capsule-v2 -->
# Managed search-object inventory — how does teable decide a generated column + GIN index is ready, stale, invalid, or missing without trusting a config table?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** A self-managing search index must reconcile against the LIVE catalog, not its own bookkeeping. What catalog columns/expressions does teable compare, and how do they collapse into a four-state inventory?

## Catalog-truth inventory (pg_attribute + pg_index + pg_get_expr + COMMENT marker)
**Path/Symbol:** `packages/v2/adapter-table-query-ops-postgres/src/searchVector.ts` — `inspectSearchVectorInventory` (2117–2207), `collectSearchVectorStaleReasons` (2278–2293), `collectSearchDocumentColumnStaleReasons` (2224–2252), `collectSearchDocumentIndexStaleReasons` (2254–2276), `resolveSearchVectorInventoryState` (2303–2311), `containsIdentifierToken` (2295–2299).
**Signature:** `inspectSearchVectorInventory(db, physical, names, fields, providerCapability): Promise<TableQuerySearchVectorInventory>` where inventory = `{state:'ready'|'missing'|'stale'|'invalid'|'unknown', semantics:'substring', provider, operatorClass, existingGeneratedColumn?, existingIndexName?, existingIndexValid?, staleReasons[]}`.
**Data Shape:** column row from `pg_attribute` LEFT JOIN `pg_attrdef` (`generation_expression` via `pg_get_expr(ad.adbin, ad.adrelid)`, `data_type` via `format_type`, `generated_kind` = `attgenerated` where `'s'`=STORED, `definition_marker` via `col_description`); index row from `pg_index` JOIN `pg_class`/`pg_am`/`pg_opclass` (`indisvalid`, `amname`, `indkey[0]`→`attname`, `indclass[0]`→`opcname` + schema).

### Decisive source
```ts
const resolveSearchVectorInventoryState = (column, index, staleReasons) => {
  if (staleReasons.length > 0) return index?.valid === false ? 'invalid' : 'stale';
  if (column && index?.valid) return 'ready';
  return 'missing';
};
// column stale checks — the expression is re-derived from the CURRENT field set:
if (column && column.data_type !== 'text') staleReasons.push('generated_column_type_mismatch');
if (column && column.generated_kind !== 's') staleReasons.push('generated_column_not_stored');
// identifier-token match so `fld_a` is not treated as present inside `fld_addr`:
if (!containsIdentifierToken(column.generation_expression, field.fieldDbName))
  staleReasons.push(`missing_field:${field.fieldDbName}`);
if (column.definition_marker !== expectedMarker) staleReasons.push('generated_expression_mismatch');
// index stale checks:
if (index && index.access_method !== 'gin') staleReasons.push('index_access_method_mismatch');
if (index && index.indexed_column !== generatedColumnName) staleReasons.push('index_column_mismatch');
if (index && index.operator_class !== providerCapability.operatorClass) staleReasons.push('index_operator_class_mismatch');
if (index && !index.valid) staleReasons.push('invalid_index');
```

**Flow:** read the single generated-column row (quoted `attname = names.generatedColumnName`, `NOT attisdropped`) and the single index row (`c.relname = names.indexName`) → rebuild the expected expression from the CURRENT field set → collect stale reasons (type/STORED/field-token/definition-marker on the column; access-method/indexed-column/operator-class/schema/valid on the index) → collapse: any stale reason ⇒ `stale` (or `invalid` if `indisvalid=false`), else both present ⇒ `ready`, else `missing`.
**Invariant:** the inventory is derived from the live catalog, never from the `table_query_search_vector_config` row — a config row can be `ready` while the physical objects are gone (⇒ `missing`) or drifted (⇒ `stale`); `invalid` is reserved for a physically-present-but-`indisvalid=false` index and outranks `stale`.
**Probe:** `searchVector.lifecycle.db.spec.ts` (491L) drives create/rebuild/drop against a real DB and asserts the resulting inventory states; unit `searchVector.spec.ts` exercises the pure helpers.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "inspectSearchVectorInventory collectSearchVectorStaleReasons resolveSearchVectorInventoryState", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt catalog-derived inventory with the stale-reason list and the stale/invalid/missing/ready collapse; adapt the exact stale-reason vocab and column/index predicates to host catalogs; omit teable's substring-specific operator-class checks if the host uses a different access method. Coverage caveat: `searchVector.ts` is parse_partial at a few template-literal lines (outside cited ranges); the inventory SQL is plain `sql<...>` tags and fully indexed.
