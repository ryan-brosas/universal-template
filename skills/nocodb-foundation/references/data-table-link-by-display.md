<!-- capsule-v2 -->
# Display-value link resolution — how do you link rows by their primary VALUE (not pk) without per-row queries or case collisions?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** When a paste-by-display-value arrives, how are display strings batch-resolved to pks with exact-first/case-insensitive-fallback, and how is the diff computed against existing links?

## nestedBulkLinkByDisplayValue internals
**Path/Symbol:** `packages/nocodb/src/services/data-table.service.ts:nestedBulkLinkByDisplayValue` (:1238-1344) + private helpers `groupEntriesByColumn` (:1350-1366), `resolveColumnGroupContext` (:1374-1395), `resolveDisplayValuesToPks` (:1408-1420), `collectLinkDiffsForGroup` (:1429-1503); shared resolver `packages/nocodb/src/helpers/ltarDisplayValueResolver.ts:resolveLtarDisplayValuesToPks`.
**Signature:** `async nestedBulkLinkByDisplayValue(context, param: { data: { columnId; rowId; displayValues: string[] }[] })` → results written back BY ORIGINAL INDEX into a pre-sized array.
**Data Shape:** Entries grouped by columnId → Map<columnId, {index, entry}[]>. Resolution returns Map<displayValue, pk>. Per entry: `{link: toLink, unlink: toUnlink}` where sets compare as `String(pk)`.

### Decisive source
```ts
// Paste resolves links by replacing the junction set (`mmList` diff), so
// it only services junction-backed relations. A column with no junction
// model (e.g. a v1 belongs-to handled via the FK column elsewhere) has
// nothing to link here.
if (!groupCtx.colOptions.fk_mm_model_id) {
  return null;
}
```
```ts
const seenPks = new Set<string>();
const matchedPks: (string | number)[] = [];
for (const value of new Set(entry.displayValues)) {
  const pk = valueToPk.get(value);
  if (pk === undefined || pk === null) continue;
  const pkStr = String(pk);
  if (seenPks.has(pkStr)) continue;
  seenPks.add(pkStr);
  matchedPks.push(pk);
}
...
// For BT/OO: only take the first match
const pksToLink = isSingleLink ? [matchedPks[0]] : matchedPks;

const existingLinkedList = await baseModel.mmList({ colId: column.id, parentId: entry.rowId }, listArgs, true);
const existingPks = (existingLinkedList || []).map((row) => dataWrapper(row).extractPksValue(relatedModel, true));

const existingPkSet = new Set(existingPks.map(String));
const newPkSet = new Set(pksToLink.map(String));
const toLink = pksToLink.filter((pk) => !existingPkSet.has(String(pk)));
const toUnlink = existingPks.filter((pk) => !newPkSet.has(String(pk)));
```

**Flow:** group entries by column (original index preserved for ordered write-back) → per group resolve context ONCE (column must be LTAR; **null when no junction** — those entries get empty diffs, not errors) → dedupe all display values across the group → two-step resolve (1. case-sensitive `eq` — one query for ALL values; 2. case-insensitive `like` fallback ONLY for misses, post-filtered by lowercase equality to avoid wildcard partials) → per entry: exist(rowId) gate → map values→pks skipping unresolved and pk-deduped → single-link relations keep only first match → mmList current links → set-diff on String(pk) → push swapEntry → deposit 'linkSwapBulkEntries' → ONE `_traceApplyLinkByDisplay` op.
**Invariant:** Unresolved display values are SILENTLY SKIPPED (continue), never an error — partial matches still yield a valid diff. The replace-semantics means toUnlink can remove pre-existing links the caller never mentioned; that is the CONTRACT of paste (replace junction set), not a bug. All set comparisons go through String() because pks may be number|string mixed. Results array must be index-addressed because grouping reorders work.
**Probe:** No runner at this pin — deterministic probe: grep confirms `resolveLtarDisplayValuesToPks(groupCtx, allUniqueValues)` is the single delegation point in this file (:1419) and `isSingleLink ? [matchedPks[0]]` appears once (:1471).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "resolveLtarDisplayValuesToPks nestedBulkLinkByDisplayValue", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt group-once → batch-resolve (exact then lowercased-equality fallback) → set-diff vs current links → single recorded apply; adopt silent-skip of unmatched values and first-match-only for single-link columns. Adapt the eq/like operator names to your query dialect. Omit the BT/OO truncation if your host has no single-target link flavor.
