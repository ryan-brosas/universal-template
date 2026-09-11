<!-- capsule-v2 -->
# lookup travel + revType — how do nested lookups resolve to their terminal column and what does relation-type inversion cover?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How does travelLookupColumn recurse through lookup chains (and when does it bail), and which relation types does getRevType deliberately NOT invert?

## lookup travel + revType
**Path/Symbol:** `packages/nocodb/src/helpers/columnHelpers.ts` — `travelLookupColumn` (:725–756), `getRevType` (:885–898).
**Signature:** `travelLookupColumn({context, column}) → Promise<Column | null>`; `getRevType(type: RelationTypes) → RelationTypes`.
**Data Shape:** recursion crosses bases via each relation's `getRelContext` refContext; error'd lookups return null.

### Decisive source
```ts
// :732–736 — the two bail-outs:
const lookupColOptions = await column.getColOptions<LookupColumn>(context);
if (lookupColOptions?.error) return null;      // broken lookup: report nothing
const relationColumn = await lookupColOptions.getRelationColumn(context);
if (!relationColumn) return null;
// :748–755 — recursion:
if (targetColumn.uidt === UITypes.Lookup) {
  return travelLookupColumn({ context: refContext, column: targetColumn });
} else {
  return targetColumn;
}
// :885–898 — inversion table:
case RelationTypes.BELONGS_TO: return RelationTypes.HAS_MANY;
case RelationTypes.HAS_MANY: return RelationTypes.BELONGS_TO;
case RelationTypes.MANY_TO_ONE: return RelationTypes.ONE_TO_MANY;
case RelationTypes.ONE_TO_MANY: return RelationTypes.MANY_TO_ONE;
return type;   // mm / oo fall through unchanged
```

**Flow:** resolve lookup options → null on stored `error` or missing relation column → load TARGET column under the RELATION's refContext → if target is itself Lookup recurse (context becomes refContext of ITS relation) else return terminal. getRevType maps four directional types to their inverses; mm/oo are direction-neutral and pass through.
**Invariant:** Broken chains degrade to null (callers treat as "no terminal"), never throw — a corrupted lookup must not crash meta projections that merely want the leaf type. Context threading matters at every level: the target is read in the RELATION's base, not the caller's.
**Probe:** `grep -c "lookupColOptions?.error" packages/nocodb/src/helpers/columnHelpers.ts` → `1`.
**Coverage caveat:** grep-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "travelLookupColumn getRevType", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt error→null degradation and per-level refContext recursion; adopt the exact four-case inversion with mm/oo pass-through.
