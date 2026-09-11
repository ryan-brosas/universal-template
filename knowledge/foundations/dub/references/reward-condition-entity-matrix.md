<!-- capsule-v2 -->
# Condition entity resolution matrix — which attributes exist per entity, and the metadata-only carve-outs

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** For a condition `{entity, attribute}`, where does the field value come from — and which entities support metadata conditions?

## Two entity maps with deliberate holes
**Path/Symbol:** `apps/web/lib/partners/evaluate-reward-conditions.ts:resolveConditionFieldValue` (:71-106).
**Signature:** `resolveConditionFieldValue({condition, context}): string | number | string[] | number[] | undefined`.
**Data Shape:** metadata branch reads `<entity>.metadata[metaKey]` (loose JSON); plain branch reads `<entity>[attribute]` directly; both return undefined on any hole.

### Decisive source
```ts
if (condition.attribute === "metadata") {
  const metaKey = condition.metadataField?.trim();

  if (!metaKey) {
    return undefined;
  }

  const entityMap = {
    partner: undefined,
    customer: undefined,
    lead: context.lead,
    sale: context.sale,
  } as const;

  return prepareMetadataFieldValue(
    entityMap[condition.entity]?.metadata?.[metaKey],
    condition,
  );
}

const entityMap = {
  partner: context.partner,
  customer: context.customer,
  lead: undefined,
  sale: context.sale,
} as const;

return entityMap[condition.entity]?.[condition.attribute];
```
(evaluate-reward-conditions.ts :78-105)

**Flow:** attribute==="metadata" → trim metadataField (empty/whitespace ⇒ undefined ⇒ condition fails closed) → metadata is readable ONLY for lead/sale entities (partner/customer hardcoded undefined) → delegate to prepareMetadataFieldValue for type coercion → else plain attribute lookup where lead has NO scalar attributes (undefined) while partner/customer/sale do.
**Invariant:** the two matrices are COMPLEMENTARY, not symmetric: partner+customer have scalars but no metadata; lead has only metadata; sale has both. A porter who "fixes" one map to match the other changes which conditions can ever match — e.g. allowing customer.metadata would make previously-dead conditions live. The zod schema layer mirrors this split (`rejects metadata attribute for entities other than lead and sale`, `rejects non-metadata attribute for lead entity` tests :2411/:2453).
**Probe:** deterministic probes (repo root): `grep -n 'condition.attribute === "metadata"' apps/web/lib/partners/evaluate-reward-conditions.ts` → :78; `grep -n 'partner: undefined' apps/web/lib/partners/evaluate-reward-conditions.ts` → :86 (metadata map); `grep -n 'lead: undefined' apps/web/lib/partners/evaluate-reward-conditions.ts` → :101 (plain map); direct-test anchors by line: `grep -n 'test("rejects metadata attribute for entities other than lead and sale"' apps/web/tests/rewards/reward-conditions.test.ts` and `grep -n 'test("rejects non-metadata attribute for lead entity"'` resolve in-suite.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "resolveConditionFieldValue", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the complementary entity matrices verbatim — they encode which reward-targeting features exist per entity. Adapt RewardContext shape. Omit nothing.
