<!-- capsule-v2 -->
# Select-options-from-values generation — how does converting into a select field mint choices (ids, colors) from existing column data without losing existing options?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** Where do new select choices come from during conversion, and what guards prevent oversized or duplicate option names?

## buildSelectOptionsFromValuesStatement
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/FieldTypeConversionVisitor.ts` — `buildSelectOptionsFromValuesStatement` (:484–554), color palette `SELECT_OPTION_COLORS` (:1676–1706, 8 bright colors cycled by index), length gate `SELECT_CHOICE_NAME_MAX_LENGTH = DEFAULT_TABLE_DATA_SAFETY_LIMITS.fieldOptions.maxSelectChoiceNameLength` (:76–79).
**Signature:** `(params, distinctValuesSql): TableSchemaStatementBuilder | null` — null when `params.fieldId` absent; statement is scope `'meta'` with BOTH a compile-time preview SQL and an execute() implementation.
**Data Shape:** generated choice = `{id: SelectOptionId.generate(), name, color: colors[index % 8]}`; merged via `buildMergedOptions(currentOptions, generatedChoices)` preserving existing choices and appending only unseen names.

### Decisive source
```ts
// execute(): data-plane DISTINCT probe + TS-side guard + meta-plane merge
const distinctRows = await sql`WITH distinct_values AS (${sql.raw(distinctValuesSql)})
  SELECT DISTINCT name FROM distinct_values WHERE name IS NOT NULL AND name <> ''`.execute(dataDb);
const oversizedName = distinctNames.find((n) => n.length > MAX_LENGTH);
if (oversizedName) throw new Error(selectChoiceNameLengthError + oversizedName);
// ... then UPDATE field SET options = JSON.stringify(mergedOptions) WHERE id = fieldId
```

**Flow:** preview SQL embeds an anti-join against oversized values so the compile-time shape documents intent; execution re-derives distinct names from the DATA plane, hard-fails the whole conversion on ANY oversized name (fail-closed rather than truncate), reads current field.options from the META plane, mints ids/colors only for names not already present, writes merged JSON back.
**Invariant:** choice IDs come from the domain generator (never hand-rolled); existing choices are never reordered or recolored; the guard is enforced in TS at execute time even though the preview SQL filters them — the throw is the contract.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/__tests__/FieldTypeConversionVisitor.pglite.spec.ts:434 describe('Select options generation')`; formula→select path exercised via buildFormulaMigrationStatements optionsStatements branch.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "generateSelectOptionsFromValues buildMergedOptions normalizeChoices SelectOptionId.generate", limit: 10 });
```

## Verdict
Adopt dual-plane (data-distinct → meta-options) choice minting with fail-closed length guards and append-only merging; adapt the palette and limit source to host design tokens; omit the preview-SQL duplication if your executor never inspects compiled text.
