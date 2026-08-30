<!-- capsule-v2 -->
# Self-rule defaults and merge-key candidates — "When does an object get timeline activities without any declared type, and which recent rows may absorb a new payload?"

**Source:** twenty-crm AGPL-3.0 `main@9e4717278c29efa3ba0c147f6acf0d68e99a625c`; Codebase Memory `ext-twenty-crm`. **Question:** What are the default activity rules for audited objects, and how do snapshot-less legacy rows coexist with snapshotted ones in coalescing?

## Two small kernels: default self-rule + candidate ladder
**Path/Symbol:** `packages/twenty-server/src/modules/timeline/utils/build-timeline-activity-self-rule.util.ts` (:1-48 whole); `packages/twenty-server/src/modules/timeline/utils/build-timeline-activity-merge-key.util.ts` (:10-41 whole).
**Signature:** `buildTimelineActivitySelfRule({flatObjectMetadata, timelineActivityTypes}) => TimelineActivityRule | undefined`; `buildTimelineActivityMergeKeyCandidates(args) => string[]`.
**Data Shape:** Self rule = {sourceFlatObjectMetadata, actions, triggerFieldNames: null, targetShape: {kind:'SELF'}}; merge key = JSON.stringify([recordId, workspaceMemberId ?? null, typeId, snapshot?.universalIdentifier, snapshot?.action, snapshot?.objectUniversalIdentifier]).

### Decisive source
```ts
const defaultActions = flatObjectMetadata.isAuditLogged && !flatObjectMetadata.isSystem
  ? DEFAULT_SELF_RULE_ACTIONS  // ['created','updated','deleted','restored']
  : [];
const actions = [...new Set([...defaultActions, ...declaredActions])];
if (!isNonEmptyArray(actions)) return undefined;
```
```ts
if (args.timelineActivityTypeSnapshot === null) return [exactKey];
return [exactKey, buildTimelineActivityMergeKey({...args, snapshot: null})];
```

**Flow:** Audited non-system objects get the four CRUD actions by DEFAULT (declared types union in; system objects need explicit declarations; empty → no rule at all). Coalescing match tries the payload's exact key first, then — only when the payload CARRIES a snapshot — the same identity with snapshot stripped, so a typed/snapshotted payload can still merge into an older row written before snapshots existed (spec: "merges and stamps a recent row written without a snapshot"); a null-snapshot payload never reaches up into snapshot-differentiated rows. Snapshot backfill on merge is one-way: only fills when the existing row's snapshot is missing.
**Invariant:** Defaults flow from audit-logging flags, not configuration files; the candidate ladder is strictly downward-specific (snapshot → none), never sideways.
**Probe:** `grep -n "'created'," packages/twenty-server/src/modules/timeline/utils/build-timeline-activity-self-rule.util.ts | head -1` → line 9 (DEFAULT_SELF_RULE_ACTIONS head); `grep -n 'timelineActivityTypeSnapshot: null,' packages/twenty-server/src/modules/timeline/utils/build-timeline-activity-merge-key.util.ts` → line 38 (candidate twin); direct test `timeline-activity.repository.spec.ts` "merges and stamps a recent row written without a snapshot".

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-twenty-crm","query":"buildTimelineActivityMergeKeyCandidates buildTimelineActivitySelfRule","limit":5,"detail":"ids"}'
```

## Verdict
Adopt flag-driven default rules and the downward-specific merge-key candidate ladder for any coalescing ledger that gained a richer identity over time. Adapt the flag pair to host audit semantics. Omit nothing. Direct spec exists upstream for both behaviors.
