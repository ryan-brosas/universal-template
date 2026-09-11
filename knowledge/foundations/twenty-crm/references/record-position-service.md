<!-- capsule-v2 -->
# record-position-service — How are records ordered without renumbering on every insert?

**Source:** twenty-crm (AGPL-3.0 — patterns only, never verbatim), main@a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0; Codebase Memory `ext-twenty-crm`. **Question:** What is the full contract of the integer-gap ordering primitive (first/last/explicit placement, batch backfill, min/max reads)?

## record-position-service
**Path/Symbol:** `packages/twenty-server/src/engine/core-modules/record-crud/../core-modules/record-position/services/record-position.service.ts` (`packages/twenty-server/src/engine/core-modules/record-position/services/record-position.service.ts`)`:RecordPositionService` (:11-256).
**Signature:** `buildRecordPosition({value: number|'first'|'last', objectMetadata:{isCustom,nameSingular}, workspaceId, index?=0}): Promise<number>`; `overridePositionOnRecords({partialRecordInputs, workspaceId, objectMetadata+fieldIdByName, shouldBackfillPositionIfUndefined}): Promise<Partial<ObjectRecord>[]>`; private `findMinPosition/findMaxPosition(...): Promise<number|null>` via `repository.minimum('position')/maximum('position')`.
**Data Shape:** positions are plain integers in a `position` column (TypeORM `minimum`/`maximum` aggregates); inputs may carry sentinel strings `'first'`/`'last'`; output mutates the caller's partial records in place and returns the same array reordered first-bucket → last-bucket → numeric → untouched (:150-155).

### Decisive source
```ts
if (recordsThatNeedFirstPosition.length > 0) {
  const existingRecordMinPosition = await this.findMinPosition(objectMetadata, workspaceId);
  const minPosition = calculatePosition(
    (positions, fallback) => Math.min(...positions, fallback),
    existingRecordMinPosition,
  );
  for (const [index, record] of recordsThatNeedFirstPosition.entries()) {
    record.position = minPosition - index - 1;
  }
}
```
(:118-132; the `'last'` twin at :134-148 mirrors with `Math.max` / `maxPosition + index + 1`.)

**Flow:** bucket by requested position kind (`'last'` → numeric → `'first'` → `undefined && shouldBackfill` → untouched; :81-96) → one `findMinPosition`/`findMaxPosition` DB round-trip **per bucket, not per record** → seed each batch from both the DB extremum AND explicit numeric positions present in the same request (`calculatePosition` folds `numericPositions` with `Math.min/max(...positions, fallback)`; :102-116) → assign descending/ascending gaps by batch index. Empty table ⇒ first record gets position `1` (`:40-42`, `:50-52`). All reads/writes run through `GlobalWorkspaceOrmManager.executeInWorkspaceContext` with `buildSystemAuthContext(workspaceId)` and `shouldBypassPermissionChecks: true` repositories (:163-183, :193-205, :212-228).
**Invariant:** never rewrite existing rows' positions — new records claim NEW gap integers outside the current `[min,max]` range (`min − index − 1`, `max + index + 1`); batch members keep input order within their bucket. Aggregates returning `NaN`/null collapse to `null` via `sanitizeNumber` (`engine/utils/sanitize-number.utli.ts:3-9`), and callers treat `null` as empty-table. If the object has no `position` field (`fieldIdByName['position']` undefined) the whole pass is a no-op passthrough (:75-79).
**Probe:** `sed -n '129,131p' packages/twenty-server/src/engine/core-modules/record-position/services/record-position.service.ts` prints `record.position = minPosition - index - 1;`; direct behavior pins live in the runner spec suite (`src/engine/api/common/common-query-runners/common-create-many-query-runner/utils/__tests__/categorize-records.util.spec.ts` exercises the insert-side bucket).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-twenty-crm", query: "overridePositionOnRecords", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the gap-integer ordering scheme (bucket once, one extremum query per bucket, fold in-request numerics into the extremum, index-based gap assignment) and the null-as-empty-table convention. Adapt repository access to your ORM (here TypeORM `minimum`/`maximum` + system auth context bypass). Omit Twenty's workspace-permission plumbing if your host has a single tenant; keep the `position`-field-missing passthrough guard either way.
