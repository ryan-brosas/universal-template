<!-- capsule-v2 -->
# Fuzzy matcher scoring — how should a fuzzy score encode typing habits without polluting normal ranking?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter's fuzzy search ranks technically-correct matches uselessly — what shape must the score have?

## Lower-is-better, muscle-memory weighted, forgiveness behind a handicap
**Path/Symbol:** `packages/tui/src/fuzzy.ts` (137L; digit-swap fallback :75-88).
**Signature:** in-order subsequence matching returning a SCORE (lower = better); multi-token AND filtering splits query on whitespace AND slashes so `api/client` behaves like a path.
**Data Shape:** Score components: consecutive-run chars −5 each (escalating), word-boundary hits −10 (boundary = string start or after whitespace/dash/underscore/slash/dot/colon), exact match −100; gaps +2/char, later positions +0.1/char. Empty queries pass everything through UNSORTED.

### Decisive source
```ts
const alphaNumericMatch = queryLower.match(/^(?<letters>[a-z]+)(?<digits>[0-9]+)$/);
const numericAlphaMatch = queryLower.match(/^(?<digits>[0-9]+)(?<letters>[a-z]+)$/);
const swappedQuery = alphaNumericMatch
	? `${alphaNumericMatch.groups?.digits ?? ""}${alphaNumericMatch.groups?.letters ?? ""}`
	: ...;
// plain match failed on a purely letters+digits query → retry SWAPPED at a +5 handicap
```

**Flow:** try the plain query first → on failure of a purely alphanumeric-patterned query (`gpt4` vs `4gpt` model-name habits), retry with digits/letters swapped and add a +5 handicap so swapped wins never outrank genuine matches → otherwise standard scoring. Boundaries reward the prefixes people actually type; empty queries preserve list order because browsing is not searching.
**Invariant:** Forgiveness must be quarantined behind a handicap and only triggered for patterns where transposition is plausible — it must never perturb default ranking for normal queries.
**Probe:** `packages/tui/test/fuzzy.test.ts:5+` ("empty query matches everything with score 0", boundary/consecutive scoring cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "fuzzyMatch score word boundary swap", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the score shape and handicap-quarantined swap fallback. Adapt weights if your lists are much longer/shorter. Omit slash-tokenization if your domain has no paths. Coverage caveat: none.
