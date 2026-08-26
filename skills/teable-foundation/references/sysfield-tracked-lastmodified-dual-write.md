<!-- capsule-v2 -->
# Tracked last-modified dual-write — when does a LastModifiedTime/By field get its own COLUMN update vs riding the system column?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does teable keep per-field "last modified" columns correct without a generated-column dependency?

## getModifiedSystemOpsMap
**Path/Symbol:** `apps/nestjs-backend/src/features/calculation/system-field.service.ts:getModifiedSystemOpsMap` (:46–185); persist loops :158–166 and :169–180.
**Signature:** `getModifiedSystemPropsMap(table: TableDomain, fieldKeyType, records): Promise<records>` (returns records with merged system fields).
**Data Shape:** Two accumulators `trackedLastModifiedColumnUpdates` / `trackedLastModifiedByColumnUpdates`: dbFieldName → recordIds.

### Decisive source
```ts
const trackedIds = lmtField.getTrackedFieldIds();
const validTrackedIds = trackedIds.filter((id) => table.hasField(id));
const configTrackAll = lmtField.isTrackAll();
const effectiveTrackAll = configTrackAll || validTrackedIds.length === 0;
const shouldUpdate = effectiveTrackAll || validTrackedIds.some((id) => changedFieldIds.has(id));
if (shouldUpdate) {
  pre[field[fieldKeyType]] = timeStr;
  // Persist column when not using generated/system value
  if (!configTrackAll) {
    const ids = trackedLastModifiedColumnUpdates[field.dbFieldName] || [];
    ids.push(record.id);
    trackedLastModifiedColumnUpdates[field.dbFieldName] = ids;
  }
}
```

**Flow:** One blanket UPDATE stamps `__last_modified_time/__last_modified_by` on all touched rows (time from CLS `tx.timeStr` fallback now; user from CLS). Per-field LastModified* fields then decide INDIVIDUALLY: track-all ⇒ response-only value (system column already stamped); track-subset ⇒ include value only if an actually-changed field is in the tracked set, AND queue a targeted column UPDATE for exactly those records. LastModifiedBy persists a SANITIZED user snapshot (`sanitizeAuditUserValue` strips avatarUrl, clones to avoid shared-mutation) JSON-stringified.
**Invariant:** `effectiveTrackAll = configTrackAll || validTrackedIds.length===0` means a filter that references only DELETED fields degrades to track-all rather than never-fires — a porter inverting this makes timestamps silently freeze. The clone-per-record of the audit user prevents cross-record aliasing of the same object.
**Probe:** `grep -cF 'effectiveTrackAll' apps/nestjs-backend/src/features/calculation/system-field.service.ts` → 4.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "getModifiedSystemOpsMap lastModifiedTime tracked", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier stamping (system columns always; tracked columns conditionally) + empty-filter-degrades-to-all rule + sanitized cloned audit snapshots; adapt column naming; omit teable's TableDomain accessors.
