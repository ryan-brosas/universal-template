<!-- capsule-v2 -->
# Dead-letter anomaly grouping — how do you present thousands of failures as a handful of actionable groups?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What is the group key and representative-item policy for failure aggregation?

## groupComputedOutboxAnomalies / recover
**Path/Symbol:** `apps/nestjs-backend/src/features/v2/computed-outbox-trigger/computed-outbox-anomaly.service.ts:groupComputedOutboxAnomalies` (:47–130), `ComputedOutboxAnomalyService.recover` (:175–246).
**Signature:** `(items, {groupLimit=30, sampleLimit=12}) => {groups, groupTotal}`; `recover({targetId, taskId, kind:'dead'|'stale'}): Promise<{delivery:'accepted'|'deferred'}>`.

### Decisive source
```ts
export const buildComputedOutboxAnomalyGroupKey = (item) =>
  [item.kind, item.baseId, item.seedTableId, (item.lastError ?? '').slice(0, 500)].join('\\u0001'); // :42–45
...
if (existing.items.length < sampleLimit) { existing.items.push(item); }        // :105 bounded samples
```

**Flow:** fetch capped at min(2000, max(groupLimit×40, 200)) rows per target across meta-fallback + BYODB with concurrency 4 (per-target errors degrade that target only); group key = kind+baseId+seedTableId+first-500-chars-of-error (control-char joined); representative item = LATEST occurredAt with taskId tiebreak; groups sorted by recency→count→key then truncated to limit; each group keeps ≤12 sample items sorted newest-first. `recover` maps dead/stale back to pending via the maintenance manager, throwing ConflictException on equivalent-pending-exists and NotFound when the anomaly vanished; post-recovery wakeup publish is best-effort (`delivery:'deferred'` on failure) since redrive will re-arm.
**Invariant:** Error-text truncation at 500 chars keeps transient suffixes (row ids, timestamps) from exploding group cardinality while preserving root-cause identity. Recovery never claims success it can't verify — delivery status is reported honestly.
**Probe:** `computed-outbox-anomaly.service.spec.ts` (:32 merge-into-groups keeps recent samples, :184 restore publishes wakeup, :213 recoverable-on-publish-failure, :232 conflict/not-found).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildComputedOutboxAnomalyGroupKey", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the composite truncating group key + honest delivery reporting; adapt exception mapping; omit Nest HTTP exceptions if not in a controller.
