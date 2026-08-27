<!-- capsule-v2 -->
# Family-head grouping — how do you collapse hundreds of variant model ids into a displayable list of family heads without hiding anything, while keeping same-id-different-provider rows distinct?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** A pi config can list 20+ model ids that are really 4 families × variants (`kimi-k2.6`, `-fast`, `-long`, …). How do you collapse them for display so the list stays short, deterministic, and *lossless* — with an exact expansion path — and never merge two selectable units that merely share a name?

## Connected graph-selected seam
**Path/Symbol:** `src/agent/model-catalog.ts:familyKey` (:184–198), `groupIntoFamilies` (:206–223), `VARIANT_SUFFIXES` (:176), `piProvider` (:402–407), `groupPiProviderLocal` (:414–427), `applyDisplayPolicy` (:434–460), `DISPLAY_CAP=5` (:108).
**Signature:** `familyKey(id: string): string`; `groupIntoFamilies(rows: CatalogModel[]): CatalogModel[]`; `applyDisplayPolicy(backend, rows, aliases, scoped): { visible; total; omitted }`.
**Data Shape:** a head row is a shallow copy of the *first-seen* row plus `variantCount = members − 1`. Input rows are never mutated.

### Decisive source
```ts
/** Trailing variant suffixes, longest-first so `short-fast` strips before
 *  `short`/`fast`. Order matters; a single regex pass over a fixed list keeps
 *  grouping deterministic and fixture-testable. */
const VARIANT_SUFFIXES = ['short-fast', 'highspeed', 'canary', 'nvfp4', 'fast', 'long', 'short', 'fp8'] as const;

export function familyKey(id: string): string {
  let base = id;
  const hf = base.indexOf('hf:');
  if (hf !== -1) base = base.slice(hf + 3);
  const slash = base.lastIndexOf('/');
  if (slash !== -1) base = base.slice(slash + 1);
  const lower = base.toLowerCase();
  for (const suf of VARIANT_SUFFIXES) {
    const suffix = `-${suf}`;
    if (lower.endsWith(suffix) && lower.length > suffix.length) {
      return lower.slice(0, -suffix.length);
    }
  }
  return lower;
}
// groupPiProviderLocal — the navigator invariant:
// "never merge across providers — same id on two providers is two
//  selectable units". Preserves provider order, then each provider's own order.
for (const prov of providerOrder) {
  out.push(...groupIntoFamilies(byProvider.get(prov)!));
}
```

**Flow:** `familyKey`: strip `hf:` prefix → strip org prefix after the last `/` → lowercase → strip at most ONE trailing variant suffix using the fixed longest-first table → unknown shapes fall out as their own singleton (the `lower.length > suffix.length` guard means `-fast` maps to `-fast`, never to an empty key). `groupIntoFamilies`: one pass building `headByKey` (first-seen shallow copy), `countByKey`, and `order`; emit heads in first-seen order with `variantCount = count − 1`. `groupPiProviderLocal`: partition rows by provider (preserving first-seen provider order), group within each provider, concatenate. `applyDisplayPolicy`: pi rows get provider-local collapse (droid rows arrive pre-collapsed as curated heads — no regroup, keep order); alias targets are split out and re-injected at the front so they survive the cap; scoped view returns the full ordered list with `omitted: 0`; unscoped view slices to `DISPLAY_CAP=5` and reports `omitted = total − visible.length`.
**Invariant:** pure and deterministic — same input always yields the same heads (fixed suffix table, first-seen order, no randomness, no clock); input rows are not mutated; nothing is ever hidden — unknown shapes become singleton heads and the scoped view expands to the complete lossless inventory; the unscoped cap is honest via exact `totalCatalogModels`/`omittedCatalogModels` accounting; **never merge across providers** for pi (same id on two providers = two selectable units); grouping is display-only and never rewrites the model string passed to a backend (file header :10–13).
**Probe:** `tests/agent/model-catalog.test.ts` (executed green at pin, part of 29 pass / 0 fail) — familyKey block pins org/hf stripping, longest-suffix-first (`glm-5.2-short-fast` → `glm-5.2`, not `glm-5.2-short`), case-collapse dedup, and the `-fast` singleton guard; groupIntoFamilies block pins first-seen head + `variantCount`, non-mutation of inputs, and that the low-level function IS provider-agnostic (provider-locality lives one layer up); collectModels block pins the end-to-end invariant: scoped pi fixture (neuralwatt 7 rows + hyper 2 rows) yields exactly 6 lossless heads with `omitted === 0` and hyper's same-named ids kept separate, while unscoped caps at ≤5 with `omitted === total − visible`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "familyKey groupIntoFamilies groupPiProviderLocal applyDisplayPolicy variantCount", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shape: a fixed longest-first suffix table (not a regex alternation) for deterministic, fixture-testable key derivation; first-seen-head collapse with explicit `variantCount`; a separate provider-locality layer so the low-level grouper stays provider-agnostic; alias-target injection before capping so user-referenced models stay visible; and exact total/omitted accounting so any cap is honest and expandable. Adapt the suffix table, cap, and canonical-id grammar to your host's model naming. Omit nothing behavioral; keep the display-only rule absolute — the moment grouping can rewrite what gets sent to the backend, it stops being a view and becomes a resolver, and this seam is not one.
