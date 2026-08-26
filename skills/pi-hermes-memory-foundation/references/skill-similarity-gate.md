<!-- capsule-v2 -->
# Skill similarity gate — one Jaccard score table splits "enhance it" from "rename it"

**Source:** pi-hermes-memory (MIT, `main@71beae8a53be2cdc4901744cf85bd65a1b3030e6`); Codebase Memory `pi-hermes-memory`. **Question:** How do you stop an agent from accumulating near-duplicate procedural skills while still allowing genuinely distinct skills with similar names — using only local token similarity, no embeddings?

## Similarity gate
**Path/Symbol:** `src/store/skill-store.ts` — `findSimilarGlobalSkillIds` (:745–755), `findNameCollisionGlobalSkillIds` (:757–767), `scoreGlobalSimilarity` (:769–795); helpers in `src/store/skill-utils.ts` — `tokenizeForSimilarity` (:80–87), `jaccardSimilarity` (:89–101), `SKILL_SIMILARITY_STOP_WORDS` (:74–78); thresholds NAME_SIMILARITY_THRESHOLD = 0.7, DESCRIPTION_SIMILARITY_THRESHOLD = 0.75; direct tests `tests/store/skill-store.test.ts:155–223`.
**Signature:** `scoreGlobalSimilarity(candidateSlug, candidateDescription) → Array<{skillId, nameSimilarity, descriptionSimilarity}>` sorted by nameSimilarity desc (ε 0.0001 tie-break → descriptionSimilarity desc).
**Data Shape:** tokens are lowercased `[a-z0-9]+` runs of length >1 minus a stop-word set that includes domain-noise words (`workflow`, `procedure`, `step(s)`, `guide`, `skill(s)`, `repo`, `project`, `use`, `using`).

### Decisive source
```ts
// The 2×2 partition over ONE scored table:
// findSimilarGlobalSkillIds (:745-755)  → name > 0.7 AND description > 0.75 ⇒ conflictType:"similar",
//                                          suggestedAction:"patch" ("Enhance the existing skill...")
// findNameCollisionGlobalSkillIds (:757-767) → name > 0.7 AND description ≤ 0.75 ⇒ conflictType:"name-collision",
//                                          suggestedAction:"rename" ("Use a clearer differentiated name...")

const candidateNameTokens = tokenizeForSimilarity(candidateSlug.replace(/-/g, " "));
const candidateDescriptionTokens = tokenizeForSimilarity(candidateDescription);
return globals.map(skill => {
  const nameTokens = tokenizeForSimilarity((skill.displayName || skill.name).replace(/-/g, " "));
  const descriptionTokens = tokenizeForSimilarity(skill.description || "");
  return { skillId: skill.skillId,
           nameSimilarity: jaccardSimilarity(candidateNameTokens, nameTokens),
           descriptionSimilarity: jaccardSimilarity(candidateDescriptionTokens, descriptionTokens) };
}).sort(...);

// jaccardSimilarity: empty EITHER side ⇒ 0 (never "infinitely similar")
if (aSet.size === 0 || bSet.size === 0) return 0;
```

**Flow:** (1) On global-scope create/move-into-global, the whole global index is scored once against the candidate. (2) High-name + high-description similarity means the SAME procedure probably exists → block create, suggest `patch` so learnings accumulate in one skill. (3) High-name but LOW description similarity means the name is taken but the intent differs → block create, suggest `rename`. (4) Low name similarity never blocks regardless of description overlap. (5) Sorting puts the best name match first so error messages cite the single most relevant existing skillId.

**Invariant:** the two gates read ONE shared scoring pass and differ ONLY in the description predicate (`>` vs `<=` at the same 0.75 threshold) — they are complementary halves of a partition, not independent heuristics, so a candidate can trigger at most one of the two outcomes per existing skill and the first gate hit wins in create's ordered chain. Name tokens come from slugs with dashes re-spaced (`replace(/-/g," ")`) so `foo-bar` matches display name "Foo Bar". Stop-word filtering prevents generic vocabulary ("workflow", "steps") from inflating similarity. Empty-token-set Jaccard is pinned to 0, making blank descriptions unable to collide.

**Probe:** `tests/store/skill-store.test.ts` — `blocks creating a similar global skill and suggests patching` (:155), `blocks near-name global collisions even when descriptions diverge` (:179), `allows creating distinct global skills` (:203). Coverage caveat: `tests/` is excluded from the graph index by design; probes are source-grounded from on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "findShadowingPiGlobalSkill findNameCollisionGlobalSkillIds jaccard", limit: 5 });
```

## Verdict
Adopt the single-score-table 2×2 partition (similar→patch vs collision→rename) with asymmetric thresholds for any LLM-authored named-record store. Adapt thresholds (0.7/0.75) and stop-word list to host vocabulary. Omit the sort/tie-break if you surface all candidates rather than citing one.
