<!-- capsule-v2 -->
# formula-select-expression-fallback — When does a formula field SELECT its physical generated column vs re-emit the expression inline?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What context flags decide `getGeneratedColumnName()` vs `convertFormulaToSelectQuery(...)`?

## rawProjection and not-persisted-as-generated both force inline recompilation
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/field-select-visitor.ts:getFormulaColumnSelector` (:287-368, inline arms :322-352).
**Signature:** `private getFormulaColumnSelector(field: FormulaFieldCore): IFieldSelectName`.
**Data Shape:** inputs: `shouldSelectRaw()` (view/tableCache contexts), `hasUnresolvedReferences(table)`, `rawProjection`, `field.getIsPersistedAsGeneratedColumn()`, timezone = field option or host default.

### Decisive source
```ts
// In raw/propagation context (used by UPDATE ... FROM SELECT), avoid referencing
// the physical generated column directly, since it may have been dropped by
// cascading schema changes (e.g., deleting a referenced base column). Instead,
// always emit the computed expression which degrades to NULL when references
// are unresolved.
if (this.rawProjection) { …formulaSql = this.dbProvider.convertFormulaToSelectQuery(…)… }
if (!field.getIsPersistedAsGeneratedColumn()) { …same inline path… }
// else: select the generated column directly
const columnName = field.getGeneratedColumnName();
```

**Flow:** errored → typed NULL → lookup-formula → CTE column path → unresolved references → typed NULL (even before reaching the column) → view/tableCache context → view's projected column → rawProjection OR not-persisted → recompile expression via dbProvider with full context (selectionMap, fieldCteMap, readyLinkFieldIds, currentLinkFieldId, timeZone, targetDbFieldType), wrapping json results in to_jsonb + db-type cast → otherwise read the stored generated column.
**Invariant:** the in-source comment is the porting warning: during schema-change windows the generated column may not exist while old rows still need values — inline recompilation is the consistency mechanism for write-path propagation. Json formulas are normalized with to_jsonb so downstream jsonb casts hold.
**Probe:** static byte-exact: `grep -n 'may have been dropped by' field-select-visitor.ts` → :315-318; upstream spec family pinning generated-column selection lives in `record-query-builder-group-quoting.spec.ts`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"getFormulaColumnSelector","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the five-arm ladder. Adapt persistence probe naming. Omit nothing.
