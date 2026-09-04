<!-- capsule-v2 -->
# Effort-tier variant collapsing — how do you merge per-effort sibling wire ids into one logical model without lying about billing?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** When a provider serves `X-low`/`X-high`/`X-thinking` as separate upstream ids, how do you present ONE selectable model that routes each effort to the right wire id?

## Pure, deterministic, idempotent collapse over hand tables + two derivation rules
**Path/Symbol:** `packages/catalog/src/variant-collapse.ts:EffortVariantFamily` (:34), `collapseEffortVariants` (:1150), `deriveThinkingPairFamilies` (:941), `deriveCursorEffortFamilies` (:828), `reconcileRetiredRouting` (:1052), `refreshCollapsedThinking` (:1113), `collapseEffortVariantsAcrossProviders` (:1358).
**Signature:** `collapseEffortVariants<T>(specs: readonly T[], table): T[]`; family `{id, members, routing: Partial<Record<Effort|"off", string>>, thinking, retiredMembers?, extraAliases?, preserveAbsentEffortRoutes?}`.
**Data Shape:** routing maps each effort (plus `"off"`) to a member wire id; the collapsed spec's local id stays stable while `requestModelId` carries the default wire id; `thinking.effortRouting` is written ONLY by collapsing (the collapsed-detection sentinel).

### Decisive source
```ts
// Idempotence contract: collapse(collapse(x)) === collapse(x), and mixed
// raw+collapsed input (stale cache rows) dedupes to the collapsed entry —
// safe at every source: discovery, generator, model-manager merge point.

// A family that routes efforts to a live thinking backing id reasons even
// when upstream metadata forgot to mark the members.
const reasoning = memberSpecs.some(spec => spec.reasoning) || hasEffortRoute;

// Price-divergent twins are DISTINCT SKUs and never merge, so billing
// attribution never lies; all-zero cost rows count as UNKNOWN (aggregators
// routinely ship them) and may merge.
if (specPriced && basePriced && (cost differs on any field)) continue;
```

**Flow:** per provider: hand table (`VARIANT_COLLAPSE_TABLES` for google-antigravity / google-gemini-cli / devin / cursor — CCA providers diverge only on thinking transport) → Cursor-only conservative live-tier derivation (`deriveCursorEffortFamilies`, gated by an 11-condition unsafe-base veto incl. independent live base SKU, existing thinking ladder, metadata divergence via `Bun.deepEquals`, tier token in product name) → global automatic `X`+`X-thinking` pair rule (`stripThinkingVariantToken`, infix tokens handled, claimed-by-hand-table ids skipped) → `retargetCollapsedModelReferences` re-keys config pointing at removed members → `registerCollapsedVariantAliases` persists embedded routing as selector aliases so old ids keep resolving.
**Invariant:** (1) one axis per family — Cursor's `-fast` service tier becomes a SIBLING family, never a second routing dimension; (2) members must be cost-homogeneous and capability-identical or the family is left expanded; (3) retired wire ids stay in `members` (raw upstream spec still consumed/aliased) but fresh routing never targets them — stale snapshots get re-pointed via `reconcileRetiredRouting` (per-entry precedence: table route → off/first-live-member → drop); (4) absent-member effort routes drop UNLESS `preserveAbsentEffortRoutes` (CCA lists bare id while accepting `-thinking` wire calls); (5) non-members pass through BY REFERENCE, order preserved.
**Probe:** direct `packages/catalog/test/variant-collapse.test.ts:96` (triplet collapse + pass-through reference identity), `:452` (pair rule: price-divergent/orphan/api-mismatch all stay separate, `:520` hand-table claims win), `:677` (Cursor Grok tiers #8803), `:788` (generic tier safety vetoes #9237), `:1249` (Devin GLM-5.2 free-quota routing).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "collapseEffortVariants deriveThinkingPairFamilies EffortVariantFamily", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the family schema, the idempotence/purity contract, the price-homogeneity gate, and retired-id reconciliation; adapt hand tables wholesale to your providers (they encode vendor wire truth); omit the Cursor live-derivation rule if your discovery already emits canonical ids. Coverage caveat: none — the test file is 1,319 lines covering every branch including three filed issues.
