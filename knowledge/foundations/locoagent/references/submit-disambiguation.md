<!-- capsule-v2 -->
# Submit-button disambiguation by snapshot adjacency — when three buttons share one accessible name, which one actually submits?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** LinkedIn renders multiple buttons named "Comment" (engagement-bar expander vs composer submit) — what positional rule picks the real submit without brittle nth-index guessing?

## Adjacency anchor ("Share photo" ⇒ next "Comment") with count-aware fallback
**Path/Symbol:** `workflows/executors/linkedin-search-reply.ts:496-529` (primary adjacency rule `:502-510`, fallback ladder `:512-522`); failure grading `:524-528`.
**Signature:** Operates on the raw accessibility-snapshot string; returns `submitRef = '@eN'` or `''` (⇒ per-post fail, loop continues).
**Data Shape:** Snapshot rows in DOM order: engagement bar emits `button "Comment" … button "Repost"` BEFORE the textbox; composer toolbar emits `button "Show Emoji Picker" … button "Share photo" … button "Comment"` AFTER it.

### Decisive source
```ts
// Strategy: find button "Comment" that appears AFTER button "Share photo" in the snapshot
// The submit button appears as: button "Show Emoji Picker" ... button "Share photo" ... button "Comment"
// The engagement bar button appears as: button "Comment" ... button "Repost"
let submitRef = ''
const sharePhotoIdx = snap2.indexOf('button "Share photo"')
if (sharePhotoIdx !== -1) {
  // Find the first button "Comment" AFTER "Share photo"
  const afterShare = snap2.slice(sharePhotoIdx)
  const submitMatch = afterShare.match(/button "Comment" \[ref=(e\d+)\]/)
  if (submitMatch) submitRef = `@${submitMatch[1]}`
}
if (!submitRef) {
  // Fallback: any Comment button that is NOT the engagement bar one
  const all = [...snap2.matchAll(/button "Comment" \[ref=(e\d+)\]/g)]
  if (all.length > 1)       submitRef = `@${all[all.length - 1]![1]}`  // last is typically submit
  else if (all.length === 1) submitRef = `@${all[0]![1]}`
}
```

**Flow:** fill the comment textbox → take a fresh snapshot → locate the stable NEIGHBOR landmark (`button "Share photo"`) → search forward from that index for the first `button "Comment"` → click it → verify by (a) own-commenter markers in the snapshot OR (b) the textbox no longer containing the comment text → only then persist to the dedup store. If the landmark is missing entirely, fall back to match-count reasoning (last of many / only one); if still nothing, grade this post failed and continue the loop.
**Invariant:** Never disambiguate same-named buttons by document order alone — anchor on a UNIQUE adjacent landmark's position (`indexOf`) and take the first target AFTER it. The fallback must be count-aware (single match ⇒ unambiguous; multiple ⇒ last-in-composer heuristic) rather than blind first-match, because the engagement bar's "Comment" expands a section instead of submitting — clicking it silently does nothing. Verification is dual-signal (identity marker OR textbox-cleared), mirroring the executor contract's verify-by-observation.
**Probe:** No upstream executor tests. Deterministic source-grounded probes: strategy comment at `linkedin-search-reply.ts:498-500`, adjacency slice at `:503-506`, count fallback at `:515-521`, dual verification at `:536-542`. Coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "comment textbox Share photo submit", limit: 10 });
```
The disambiguation lives inside top-level `main` (:253-573) — use file-pattern retrieval on `linkedin-search-reply.ts`; companion symbols `callDeepSeek` :216 resolve directly.

## Verdict
Adopt landmark-adjacency selection for duplicate accessible names plus the count-aware fallback and dual-signal verification. Adapt landmarks to your target's composer anatomy (any platform with N+1 same-named buttons needs an equivalent unique neighbor). Omit naive `getByRole('button', { name: 'Comment' }).first()` style ports — that is precisely the wrong-click bug this capsule prevents.
