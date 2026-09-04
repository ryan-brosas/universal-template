<!-- capsule-v2 -->
# Score formula — how are winning options ranked and what makes a "top choice"?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** How does the server compute option scores from raw votes, and how must the client mirror it so highlighting agrees?

## getPollResults lexicographic score + client getScore
**Path/Symbol:** `apps/web/src/features/poll/data.ts:getPollResults` (lines 80–113); client mirror `apps/web/src/features/poll/components/poll-context.tsx:PollContextProvider` (lines 45–76).
**Signature:** server: `score = (yesCount + ifNeedBeCount) * 1000 + yesCount`, `isTopChoice = score === highScore && score > 0`; client: `highScore` seeded at 1 (so all-zero polls highlight nothing).
**Data Shape:** one SQL groupBy `(optionId, type) → count` over live participants; per-option `{ yes, ifNeedBe, no }` counts.

### Decisive source
```ts
// Calculate scores for each option
// Ranking: total availability (yes + ifNeedBe) is primary, yes votes as tiebreaker
// Score formula: (yes + ifNeedBe) * 1000 + yes
const score = (yesCount + ifNeedBeCount) * 1000 + yesCount;
const highScore = Math.max(...optionResults.map((o) => o.score), 0);
const options = optionResults.map((option) => ({
  ...option,
  isTopChoice: option.score === highScore && option.score > 0,
}));
```
```ts
const highScore = poll.options.reduce((acc, curr) => {
  const { yes, ifNeedBe } = getScore(curr.id);
  const score = yes + ifNeedBe;
  return score > acc ? score : acc;
}, 1);
```

**Flow:** votes aggregated by (optionId,type) excluding deleted participants → availability total weighted ×1000 with yes-count as the ones-digit tiebreaker → ties share top-choice; an all-zero poll has highScore 0 and NO top choice. The client recomputes the same ranking live from its participants array for optimistic UI, seeding max at 1 so a fresh poll shows nothing highlighted.
**Invariant:** ordering is availability-first with yes as strict tiebreak — sorting by raw yes counts (a natural wrong port) ranks 5-yes-0-ifNeedBe above 5-yes-4-ifNeedBe. The ×1000 multiplier assumes participant count < 1000 — which is enforced: MAX_PARTICIPANTS=1000 caps votes per option.
**Probe:** deterministic grep anchors: `grep -cF '(yesCount + ifNeedBeCount) * 1000' apps/web/src/features/poll/data.ts` → 1; `grep -n '}, 1);' apps/web/src/features/poll/components/poll-context.tsx` → line 76.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "getPollResults highScore isTopChoice", limit: 5 });
```

## Verdict
Adopt the formula + MAX_PARTICIPANTS coupling verbatim; adapt the aggregation to your ORM's groupBy; omit the PostHog-free client memoization details. Server path has no dedicated unit test — the formula lives in comment-pinned source only.
