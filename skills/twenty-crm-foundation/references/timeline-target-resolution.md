<!-- capsule-v2 -->
# Unified target resolution — "How does a timeline rule find its activity target identically for direct-relation and junction events?"

**Source:** twenty-crm AGPL-3.0 `main@9e4717278c29efa3ba0c147f6acf0d68e99a625c`; Codebase Memory `ext-twenty-crm`. **Question:** How is target extraction unified across target shapes without duplicating per-shape resolvers?

## resolveTargetFromRecord — one reader, shape-gated
**Path/Symbol:** `packages/twenty-server/src/modules/timeline/services/timeline-activity-target-query.service.ts:resolveTargetFromRecord,readTargetFromRecord` (:91-100, :14-30).
**Signature:** `resolveTargetFromRecord({rule, record}) => {targetObjectNameSingular, targetRecordId} | undefined`.
**Data Shape:** record = junction row OR direct-relation-bearing source record (before/after selected by polarity); targetJoinColumns = [{joinColumnName, targetObjectNameSingular}] derived at plan build (morph relations EXPAND to sibling morph fields via findAllOthersMorphRelationFlatFieldMetadatasOrThrow; FlatEntityMapsException → [] → rule dropped as invalid).

### Decisive source
```ts
if (!isDefined(record) || rule.targetShape.kind === 'SELF') return undefined;
return readTargetFromRecord(record, rule.targetShape.targetJoinColumns);
// readTargetFromRecord: first join column with a non-empty-string id wins
```

**Flow:** The old pair (`resolveTargetFromJunctionRecord` + `resolveTargetFromDirectRelationRecord`) duplicated the same column-walk behind different kind gates. Unification: only SELF is excluded; both relation shapes share identical join-column semantics because buildDirectRelationTargetShape/buildJunctionTargetShape both produce {kind, targetJoinColumns} — shape differences live entirely in PLAN CONSTRUCTION (MANY_TO_ONE → direct; ONE_TO_MANY + junctionTargetFieldId → junction), not in event-time reading. Junction fan-out queries still use resolveTargetsBySourceRecordId (In(sourceRecordIds) over junction rows) for batched back-fill.
**Invariant:** Event-time target reading must not branch on how the shape was BUILT — first non-empty join-column value in declared order IS the target. Morph-field expansion happens once at plan time so runtime never sees morph ambiguity.
**Probe:** `grep -n "targetShape.kind === 'SELF'" packages/twenty-server/src/modules/timeline/services/timeline-activity-target-query.service.ts` → line 98 (sole remaining kind gate); `grep -n 'resolveTargetFromJunctionRecord' ...` → no matches.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-twenty-crm","query":"resolveTargetFromRecord readTargetFromRecord","limit":5,"detail":"ids"}'
```

## Verdict
Adopt plan-time shape construction + uniform event-time reading. Adapt join-column derivation to host metadata. Omit the NestJS repository plumbing. Caveat: covered indirectly by f535ca42 service regression suite (direct repointing as unlinked-old + linked-new); deterministic grep pins here.
