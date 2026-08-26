<!-- capsule-v2 -->
# Unique-longest-run sequence matcher — when is a shared run UNUSABLE as an alignment anchor, and how do you know in O(n log n)?

**Source:** billion-context-pi (MIT) `master@1c87eb5051e0e97bb6ba606dc1c57ec2510f1b41`; Codebase Memory project `mnt-hdd-utopia-inspo-coding-agents-billion-context-pi`. **Question:** Given a persisted message list and a live list (which may contain not-yet-persisted tail messages), what is the contract for finding THE unique alignment between them — and for correctly refusing when none exists?

## Suffix-array + LCP over interned keys, with uniqueness counted ACROSS the boundary
**Path/Symbol:** `src/sequence-match.ts` whole (105L): `findUniqueLongestRun` (:7-70), `buildSuffixArray` (:72-89), `buildLcp` (:91-105); consumers `src/runtime.ts`:107-135 (`mergeLiveEntries` — two independent matchers: persisted-identities vs live, and prior-turn origin identities vs live).
**Signature:** `findUniqueLongestRun<Key>(candidates: readonly Key[], live: readonly Key[]): MatchRange | undefined` where `MatchRange = { candidateStart, liveStart, length }`.
**Data Shape:** both sequences are interned into integer ids (`Map<Key, number>`, first-seen order), concatenated as `candidates + [separator] + live` — the separator id (`ids.size + 1`) can never occur in either input, so no match can span the boundary.
### Decisive source
```ts
// sequence-match.ts:41-69 — the uniqueness contract. Group suffix-array
// neighbors whose LCP >= bestLength; count ALL cross-source pairs; the run
// qualifies ONLY if exactly one pair exists globally:
let pairCount = 0;
for (let start = 0; start < suffixArray.length;) {
  let end = start;
  while (end + 1 < suffixArray.length && lcp[end + 1]! >= bestLength) end++;
  if (end > start) {
    const candidateStarts: number[] = []; const liveStarts: number[] = [];
    for (let index = start; index <= end; index++) { ...collect per source... }
    const groupPairs = candidateStarts.length * liveStarts.length;
    pairCount += groupPairs;
    if (groupPairs === 1) { uniqueCandidateStart = ...; uniqueLiveStart = ...; }
    if (pairCount > 1) return undefined;   // early exit: ambiguity anywhere kills it
  }
  start = end + 1;
}
return pairCount === 1 ? { candidateStart, liveStart, length: bestLength } : undefined;
```
**Flow:** build suffix array of the id sequence (prefix-doubling sort with rank-pair comparison and early exit when final rank == n−1) → Kasai-style LCP → scan adjacent suffix pairs keeping only CROSS-SOURCE pairs (leftSource !== rightSource; middle separator suffix excluded via `undefined`) to find bestLength → group maximal LCP plateaus and count cross pairs → accept iff total pairCount === 1. Consumer semantics (`runtime.ts`): matched live positions adopt the persisted entry's STABLE id (and migrate any refs pointing at the old `live-N` placeholder); unmatched tails get fresh `live-N` ids; two matcher calls cover "persisted branch" and "origins from the previous round" so ids stay stable across rounds even before persistence catches up.
**Invariant:** (1) The matcher returns `undefined` BOTH for "no common run" AND "ambiguous alignment" — callers must treat undefined as NO MATCH, never retry or guess; a wrong anchor here would attach compressed-block message references to the WRONG messages. (2) Repeated tokens ≠ repeated alignments: a periodic run that occurs once in each source still yields pairCount 1 and matches (test :40); two distinct max-length runs ANYWHERE fail the whole call (tests :21/:26). (3) The separator trick is what makes "longest COMMON subsequence" impossible to fake across sources — without it, LCP grouping could bridge candidate-tail to live-head. (4) Interning by first-seen order makes the algorithm work for ANY hashable key (strings OR symbols — runtime passes `MatchKey = string | symbol`, symbols representing deliberately-unmatchable entries).
**Probe:** `cd /mnt/hdd/utopia/inspo/coding-agents/billion-context-pi && npx tsx --test tests/sequence-match.test.ts` — GREEN at pin incl. the brute-force cross-check property test (:49).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-coding-agents-billion-context-pi", query: "findUniqueLongestRun MatchRange suffix array mergeLiveEntries", limit: 10 });
```

## Verdict
Adopt the whole module verbatim (it is dependency-free and host-agnostic) plus the refusal discipline: uniqueness must be evaluated across ALL maximal runs, not per-run. Adapt the Key type to your identity tuples. Do NOT substitute a naive longest-common-substring scan — O(n²) behavior on long sessions and, worse, silent acceptance of ambiguous anchors are both real porting bugs this design exists to prevent.
