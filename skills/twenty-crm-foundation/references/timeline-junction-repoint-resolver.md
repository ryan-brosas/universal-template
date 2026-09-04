<!-- capsule-v2 -->
# Junction repoint dual-emission resolver — "How does one junction-row update emit BOTH the unlinked (old target) and linked (new target) activities?"

**Source:** twenty-crm AGPL-3.0 `main@9e4717278c29efa3ba0c147f6acf0d68e99a625c`; Codebase Memory `ext-twenty-crm`. **Question:** What decides which timeline rule-action a database event maps to, per event source and target shape?

## resolveTimelineActivityRuleAction — source/junction dispatch table
**Path/Symbol:** `packages/twenty-server/src/modules/timeline/utils/resolve-timeline-activity-rule-action.util.ts:resolveTimelineActivityRuleAction` (:16-61).
**Signature:** `({actions, targetShape, eventAction, eventSource: 'SOURCE'|'JUNCTION'}) => TimelineActivityRuleAction | undefined`.
**Data Shape:** actions = declared per-type action list; SOURCE_EVENT_ACTIONS identity map {created→created, updated→updated, deleted→deleted, restored→restored}.

### Decisive source
```ts
if (eventSource === 'SOURCE' && isDefined(sourceEventAction) &&
    actions.includes(sourceEventAction)) return sourceEventAction;
// shape/source mismatch → undefined:
(eventSource === 'SOURCE' && targetShape.kind !== 'DIRECT_RELATION') ||
(eventSource === 'JUNCTION' && targetShape.kind !== 'JUNCTION') → undefined
created|restored + declared 'linked' → 'linked'
deleted + declared 'unlinked' → 'unlinked'
updated → actions.find(a => a === 'linked' || a === 'unlinked')
```

**Flow:** A junction-row UPDATE used to be hard-coded `'linked'` (old JUNCTION_EVENT_ACTIONS map) so repointing emitted only the new link. Now EACH through-rule resolves its own action from the same declared list: the old-target's type finds `'unlinked'` first, the new-target's type finds `'linked'` — both fire from one event, reading before-record for unlinked/deleted and after-record for linked/created/restored (`resolveEventRecordForRuleAction`, service :57-71). Source-record events take the identity branch ONLY for DIRECT_RELATION shapes; junction-row events never masquerade as source updates (spec: "does not treat a junction-row update as a source-record update"); SELF rules derive no link actions.
**Invariant:** Action resolution is data-driven off each type's DECLARED actions, not hard-coded per event source; record selection follows polarity (before for unlink/delete, after for link/create/restore). The `actions.find` order makes linked-vs-unlinked coexistence deterministic (first declared wins).
**Probe:** `grep -c "eventSource === 'SOURCE'" packages/twenty-server/src/modules/timeline/utils/resolve-timeline-activity-rule-action.util.ts` → 2; direct test `src/modules/timeline/utils/__tests__/resolve-timeline-activity-rule-action.util.spec.ts` (parametric matrix incl. both repoint sides).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-twenty-crm","query":"resolveTimelineActivityRuleAction eventSource junction","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the two-axis resolver (event source × target shape → action, filtered by declarations) plus before/after polarity selection for any link-transition activity system. Adapt action vocabulary to host domain. Omit nothing behavioral. Direct parametric spec exists upstream — port it with the util.
