<!-- capsule-v2 -->
# Search access-path definition builder — how is a deterministic, caller-untrusted search document definition derived from a table?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do semantics/provider/language choices compile into a definition key that uniquely identifies the physical access path?

## Semantics↔provider mutual-exclusion + field-walking definitionKey
**Path/Symbol:** `packages/v2/table-query-ops/src/searchVectorDefinition.ts` whole (128L): `buildTableSearchAccessPathDefinition` (:40-123), `languageConfigPattern = /^[\w.]+$/` (:38), `definitionKey` composition (:94-96), legacy aliases (:125-128: `buildTableSearchVectorDefinition === buildTableSearchAccessPathDefinition`).
**Signature:** `(table: Table, options?: {semantics? 'substring'|'lexical', provider? 'pg_trgm'|'pg_bigm'|'tsvector', languageConfig?, fieldIds?}) → Result<TableSearchAccessPathDefinition, DomainError>`.
**Data Shape:** defaults semantics=substring, provider=substring?'pg_trgm':'tsvector', languageConfig='simple'. Output carries `accessPath` ('generated_text' for substring / 'generated_tsvector' for lexical / 'none' when zero fields), matching `indexKind` (gin_trgm/gin_bigm/gin_tsvector/none), `scope` selected/all_fields, and per-field `{fieldId, fieldDbName, textProjection:'text_cast'}`.

### Decisive source
```ts
if (semantics === 'substring' && provider === 'tsvector')
  return err(validation('Substring search requires an n-gram provider'));
if (semantics === 'lexical' && provider !== 'tsvector')
  return err(validation('Lexical search requires the tsvector provider'));
…
const definitionKey = `${tableId}:${semantics}:${provider}:${semantics === 'lexical' ? languageConfig : 'none'}:${fields.map(f => `${f.fieldId}=${f.fieldDbName}`).join(',')}`;
```

**Flow:** validate pair → sanitize language config (trim, regex; lexical-only inclusion in key) → walk table fields (selected set or all) via `SearchDocumentFieldContributionVisitor`: not-included ⇒ skippedFields, unresolvable dbFieldName ⇒ skip with reason `unsupported_search_field_type`, else mint a text-cast contribution → compose definitionKey from table+semantics+provider+language+ordered field list.
**Invariant:** Callers may pass FIELD IDS but never physical column names — dbFieldNames always resolve through the domain (`field.dbFieldName()`), which is what makes the definitionKey trustworthy as an identity for rebuild-vs-create decisions. Empty field set degrades to accessPath 'none' instead of erroring. The languageConfig slot is 'none' for substring so substring keys are stable regardless of locale settings.
**Probe:** `searchVectorDefinition.spec.ts:49` "builds a deterministic substring document definition by default"; :74 "uses selected field ids without accepting physical column names from callers"; :86 lexical non-substring.
**Coverage caveat:** none — three direct specs pin determinism, id-only selection, and the pairing rule.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildTableSearchAccessPathDefinition definitionKey SearchDocumentFieldContributionVisitor", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the derived-not-supplied physical-name rule and composite identity key; adapt the provider matrix; keep both legacy aliases pointing at one implementation during migration windows.
