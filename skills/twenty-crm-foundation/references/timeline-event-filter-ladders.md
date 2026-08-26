<!-- capsule-v2 -->
# Update-event filter ladders — "Which updated events survive as timeline activities when only some fields changed?"

**Source:** twenty-crm AGPL-3.0 `main@9e4717278c29efa3ba0c147f6acf0d68e99a625c`; Codebase Memory `ext-twenty-crm`. **Question:** How do trigger-field and join-column change filters compose so unrelated updates never produce link/update noise?

## Two-stage filtering: link-change gate then rule-match gate
**Path/Symbol:** `packages/twenty-server/src/modules/timeline/services/timeline-activity.service.ts` (:288-304 source plane, :431-448 junction plane); `doesTimelineActivityLinkChange.util.ts` (:1-22 whole).
**Signature:** `ruleMatchesEvent({rule, ruleAction, event}): boolean`; `doesTimelineActivityLinkChange({event, joinColumnNames}): boolean`.
**Data Shape:** event.properties carries EITHER updatedFields (name list) OR diff (column → {before,after}); rule.triggerFieldNames = null (any field) or resolved field-name list from declared triggerFieldUniversalIdentifiers (unresolvable identifiers silently dropped at plan build).

### Decisive source
```ts
// source rules: plain 'updated' actions pass; link-shaped actions need a join-column change
rule.targetShape.kind !== 'DIRECT_RELATION' || action !== 'updated' ||
ruleAction === 'updated' || doesTimelineActivityLinkChange({event, joinColumnNames})
// junction rules: EVERY updated must touch source OR target join columns
action !== 'updated' || doesTimelineActivityLinkChange({
  event, joinColumnNames: [junctionSourceJoinColumnName, ...targetJoinColumns.map(c => c.joinColumnName)] })
// then per-rule:
if (!rule.actions.includes(ruleAction)) return false;
if (ruleAction !== 'updated' || !isDefined(rule.triggerFieldNames)) return true;
return isDefined(diff) && rule.triggerFieldNames.some(n => n in diff);
```

**Flow:** For updates, the link-change gate runs FIRST with dual-format support (updatedFields list preferred, diff object fallback) — an update that doesn't repoint any join column dies before type resolution. Survivors hit ruleMatchesEvent: declared-actions membership, then trigger-field restriction applies ONLY to plain 'updated' actions (link actions ignore trigger fields by design — the repoint itself is the trigger). Non-update events skip both gates.
**Invariant:** A trigger-field-restricted rule still fires on ANY declared action other than 'updated'; missing diff on an updated action means NO match (fail-closed), not unconditional fire.
**Probe:** `grep -cn 'doesTimelineActivityLinkChange({' packages/twenty-server/src/modules/timeline/services/timeline-activity.service.ts` → 2 call sites (:297 direct, :438 junction); covered behaviorally by f535ca42 regression suite ("suppression of unrelated junction updates"); deterministic pin = count + line numbers above.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-twenty-crm","query":"ruleMatchesEvent doesTimelineActivityLinkChange","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the ordered gate composition (shape/link gate → declaration membership → trigger-field restriction) for change-driven activity systems. Adapt the dual-format reader to host event shapes. Omit nothing. Caveat: service-level behavior has no dedicated unit file beyond f535ca42's suite; probes are deterministic greps.
