<!-- capsule-v2 -->
# Module selection strategy ladder — how do you pick k reasoning prompts via Thompson Sampling, low-count exploration, specifiers, or uniform mode?

**Source:** veda MIT `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`; Codebase Memory `veda`. **Question:** What is the exact precedence of module-selection strategies, and how does the bandit avoid over-exploiting early winners?

## selectModules dispatch + Beta-posterior sampling
**Path/Symbol:** `src/core/modules.ts:selectModules` (:387-419), `parseModuleSpecifier` (:432-…), `selectFromSpecifiers` (:483-556), `selectLowCountMix` (:567-…), `selectFromCategories` (:629-659), `selectDefault` (:667-713), `selectOneWeighted` (:789-816), legacy aliases table (:421-430).
**Signature:** `selectModules({k, categories?, modules?, registry?, winRates?, lowCountModules?, allowDuplicateCategoriesInSpecifiers?}): ReasoningModule[]`; k validated 1..12.
**Data Shape:** winRates keyed `"${category}/${id}"` → `{wins, appearances}`; Thompson sample = `sampleBeta(wins+1, losses+1)` (Laplace smoothing prior); 42 modules / 9 categories (2-7 per category) pinned by test.

### Decisive source
```ts
if (modules && modules.length > 0) {
  return selectFromSpecifiers(modules, registry, { allowDuplicateCategoriesInSpecifiers });
}
const useLowCount = !!lowCountModules && !!winRates && winRates.size > 0;
if (categories && categories.length > 0) {
  return selectFromCategories(k, categories, registry, winRates, useLowCount);
}
if (useLowCount) { return selectLowCountDefault(k, registry, winRates); }
return selectDefault(k, registry, winRates);
...
// Beta(wins+1, losses+1) - Laplace smoothing prior
const sample = sampleBeta(wins + 1, losses + 1);
```

**Flow:** explicit specifiers WIN outright (k derived from specifier count; duplicates across categories throw unless allowed; category-only specifiers randomize within category avoiding repeats until exhausted; legacy snake_case ids remapped e.g. `critical_thinking`→`assumption_analysis`; dash/underscore normalization) → category-constrained: distributeKAcrossCategories round-robins k over category capacities, then per-category weighted/uniform sample, result shuffled → low-count mix: k≥2 reserves ONE elite slot (top Wilson lower bound of top-10 pool), rest go to least-seen modules with random tiebreaks → default: k≤categories picks k distinct categories then one module each; k>categories round-robins all categories without repeats.
**Invariant:** Selection is WITHOUT replacement within a run (no two solvers share a module unless specifiers allow it); unseen modules get Beta(1,1) so exploration is automatic — never seed winRates with wins-only data; the elite quota is at most ONE slot even for large k.
**Probe:** `tests/core/modules.test.ts` (:15 "42 modules across 9 categories", :87-130 k/category ladders incl. k=12 round-robin, :131-188 low-count 3+1 split ×2, :189-258 specifier forms incl. duplicate-category rules) — EXECUTED this pass: pass / 0 fail at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "selectOneWeighted Beta posterior thompson", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the four-way dispatch order and Beta(wins+1, losses+1) sampling for any prompt/portfolio bandit. Adapt the module catalog and alias table to your domain. Omit Wilson-bound elite logic if you want pure Thompson Sampling.
