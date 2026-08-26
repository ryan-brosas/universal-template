<!-- capsule-v2 -->
# Insert link-title fill SQL — how do you fill missing link cell titles with a JOIN at INSERT time instead of a second UPDATE?

**Source:** teable AGPL-3.0 `develop@06a4461e2bc5`; Codebase Memory `teable`. **Question:** How does an INSERT produce fully-populated link JSON (id + title) when the caller supplied only foreign record ids, without a post-insert update pass?

## Title-fill expression builder
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/buildFilledLinkValueExpression.ts:buildFilledLinkValueExpression` (:9–75); consumed by `RecordInsertBuilder.ts` :379–394.
**Signature:** `buildFilledLinkValueExpression({linkField, linkItems, fillLinkTitleForeignTables?}): Result<RawBuilder<unknown> | null, DomainError>`.
**Data Shape:** Returns `null` when the foreign table isn't in `fillLinkTitleForeignTables` (caller has no metadata → keep raw value; NOT an error). Errors only on `isMultipleValue() && linkItems.length > MAX_FILLED_LINK_VALUE_ITEMS (20_000)` → `validation.field.link_title_fill_limit_exceeded`.

### Decisive source
```ts
// multi-value: one scalar subquery producing the whole jsonb array
sql`(
  SELECT COALESCE(jsonb_agg(jsonb_build_object(
      'id', v.id, 'title', COALESCE(v.title, ${sql.ref(`ft.${lookupDbFieldName}`)}::text)
    ) ORDER BY v.ord), '[]'::jsonb)
  FROM (VALUES ${valuesSql}) AS v(id, title, ord)   -- (item.id, item.title ?? null, index)
  LEFT JOIN ${sql.table(foreignDbTableName)} ft ON ft.__id = v.id
)`
```
Single-value twin (:66–73): `jsonb_build_object('id', v.id, 'title', COALESCE(v.title, ft.lookup))` from a 2-column VALUES row. The lookup field is resolved by `linkField.lookupFieldId()` against the foreign table's fields.
**Flow:** builder normalizes raw value (`normalizeStoredLinkItems`) → fills only when `context.fillLinkTitles && some(item.id && !item.title)` → builds this expression and OVERWRITES `values[dbFieldName]` inside the main INSERT — the title resolution rides the insert itself.
**Invariant:** COALESCE preserves caller-supplied titles (`v.title`) and only falls back to the joined lookup column for missing ones; `ORDER BY v.ord` pins array order to input order — dropping it makes jsonb_agg order undefined and breaks deterministic snapshots. Missing foreign rows LEFT JOIN to NULL titles rather than dropping items.
**Probe:** `insert/RecordInsertBuilder.spec.ts` :243–271 — compiled main INSERT must contain `LEFT JOIN "bseLegacy"."Legacy_Name" ft` and `"ft"."Primary_Field"`, and must NOT contain the foreign table id literal.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildFilledLinkValueExpression fillLinkTitles", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the in-INSERT VALUES+LEFT JOIN+jsonb_agg pattern for missing-title fill with the 20k cap and null-return-when-no-metadata contract. Adapt kysely `RawBuilder` composition and teable's `LinkField`/`Table` accessors. Omit teable's specific avatar/user snapshot plumbing around it. Coverage caveat: pinned by the recording-driver spec above (SQL-shape level); runtime jsonb behavior is exercised by upstream e2e suites not present as unit specs.
