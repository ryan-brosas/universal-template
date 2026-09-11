<!-- capsule-v2 -->
# Timeline routing-plan cache — "How does a per-workspace derived routing table stay fresh without re-deriving on every event batch?"

**Source:** twenty-crm AGPL-3.0 `main@9e4717278c29efa3ba0c147f6acf0d68e99a625c`; Codebase Memory `ext-twenty-crm`. **Question:** How are metadata-derived rules cached so schema edits invalidate them but event storms don't?

## Hash-keyed single-slot workspace cache
**Path/Symbol:** `packages/twenty-server/src/modules/timeline/services/timeline-activity-routing-plan.service.ts:routingPlanByWorkspaceId,getRoutingPlan` (:41-44, :99-132).
**Signature:** `Map<workspaceId, {cacheKey: string; routingPlan}>`; cacheKey = `['flatObjectMetadataMaps','flatFieldMetadataMaps','flatTimelineActivityTypeMaps'].map(hashes).join('|')`.
**Data Shape:** Routing plan = { activeTimelineActivityTypes, throughRules, eligibleNonAuditedObjectMetadataIds: Set<string>, flatFieldMetadataMaps, resolveTimelineActivityType } — everything the listener gate AND payload builders need, derived once.

### Decisive source
```ts
const { data, hashes } = await ...getOrRecomputeManyOrAllFlatEntityMapsWithHashes({...});
const cacheKey = [hashes.flatObjectMetadataMaps, hashes.flatFieldMetadataMaps,
  hashes.flatTimelineActivityTypeMaps].join('|');
const cachedRoutingPlan = this.routingPlanByWorkspaceId.get(workspaceId);
if (cachedRoutingPlan?.cacheKey === cacheKey) {
  return cachedRoutingPlan.routingPlan;
}
```

**Flow:** getRoutingPlan fetches flat-entity maps WITH content hashes (cheap when cached upstream) → hash-triple equality means metadata unchanged → return derived plan; any metadata edit changes ≥1 hash → rebuild: resolve declared types → partition conflicts into diagnostics buckets (ambiguous-declared-rule / ambiguous-resolver / invalid-contract via reportAll) → build through-rules with DIRECT_RELATION-or-JUNCTION target shapes (buildDirectRelationTargetShape tried FIRST, junction fallback) → collect eligible non-audited object ids.
**Invariant:** ONE service now owns both concerns the old pair split across two caches: shouldProcessEvent gate (audited objects short-circuit true; others need membership in eligibleNonAuditedObjectMetadataIds — which includes junction object ids and even rule-less objects that merely DECLARE types) and getRulesForEventBatch provision. Two overlapping caches = two staleness windows; one keyed by the same hashes = one. Single slot per workspace is correct because a stale entry can only be replaced, never merged.
**Probe:** `grep -n 'hashes.flatTimelineActivityTypeMaps' packages/twenty-server/src/modules/timeline/services/timeline-activity-routing-plan.service.ts` → line 116 (inside join('|') key); superseded file gone: `ls packages/twenty-server/src/modules/timeline/services/timeline-activity-event-eligibility.service.ts` → No such file or directory.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-twenty-crm","query":"getRoutingPlan cacheKey hashes routingPlan","limit":5,"detail":"ids"}'
```

## Verdict
Adopt hash-keyed derived-plan caching for any metadata-driven rule engine: derive once per metadata version, share across gating and provisioning. Adapt the hash source to whatever content-versioning the host has. Omit the NestJS DI specifics. Caveat: no dedicated upstream unit spec for this service (behavior covered indirectly via f535ca42's service regression suite); probes here are deterministic greps.
