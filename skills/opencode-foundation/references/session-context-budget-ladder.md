<!-- capsule-v2 -->
# Session context budget ladder — how does opencode decide "context is full" and which turns survive compaction?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How is usable context computed and how are recent turns selected for preservation when a session compacts?

## Usable-context arithmetic
**Path/Symbol:** `packages/opencode/src/session/overflow.ts` (whole file, 34L; `usable` :10–20; `isOverflow` :22–34).
**Signature:** `usable({cfg, model, outputTokenMax?}) → number` / `isOverflow({cfg, tokens, model, outputTokenMax?}) → boolean`.
**Data Shape:** `model.limit.context` and optional `model.limit.input` are provider-declared token ceilings; `tokens` is the assistant message's `{input, output, reasoning, cache:{read,write}}` block.

### Decisive source
```ts
// overflow.ts:8-19
const COMPACTION_BUFFER = 20_000
export function usable(input) {
  const context = input.model.limit.context
  if (context === 0) return 0                       // unknown context ⇒ 0 usable
  const reserved =
    input.cfg.compaction?.reserved ??
    Math.min(COMPACTION_BUFFER, ProviderTransform.maxOutputTokens(input.model, input.outputTokenMax))
  return input.model.limit.input
    ? Math.max(0, input.model.limit.input - reserved)          // explicit input cap wins
    : Math.max(0, context - ProviderTransform.maxOutputTokens(input.model, input.outputTokenMax))
}
// overflow.ts:31-33 — overflow counts EVERYTHING the request will bill
const count =
  input.tokens.total || input.tokens.input + input.tokens.output + input.tokens.cache.read + input.tokens.cache.write
return count >= usable(input)
```

**Flow:** `usable()` prefers an explicit `limit.input` over the derived `context − maxOutput` formula; reservation defaults to `min(20_000 buffer, model max output tokens)` or config override `compaction.reserved`. `isOverflow` short-circuits FALSE when `compaction.auto === false` or `limit.context === 0` (unknown context never triggers auto-compaction), otherwise compares total billed tokens against usable.
**Invariant:** A porter must count cache.read AND cache.write in the total — omitting cached tokens makes a long session look fresh and skips compaction until hard failure. `total`, when the provider supplies it, REPLACES the sum (never added to it). Context 0 means "unknown", not "empty".
**Probe:** `packages/opencode/test/session/compaction.test.ts:382` `session.compaction.isOverflow` — ":384 returns true when token count exceeds usable context" (75k+5k vs 100k context), ":408 includes cache.read in token count" (60k+10k+10k read ⇒ true at 100k), ":420 respects input limit for input caps".

## Tail-turn selection under a token budget
**Path/Symbol:** `packages/opencode/src/session/compaction.ts` (:115–163 helpers; layer `select` :223–269).
**Signature:** `preserveRecentBudget({cfg, model})` / `turns(messages)` / `splitTurn({messages, turn, model, budget, estimate})` / service `select({messages, cfg, model}) → {head, tail_start_id}`.
**Data Shape:** `Turn = {start, end, id}` spans from one real user message to just before the next (`end` initialized to array length then back-filled :134-136); turns containing a `compaction` part are EXCLUDED as turn starts (:127). `Tail = {start, id}` marks where preserved history begins.

### Decisive source
```ts
// compaction.ts:115-120 — budget = 25% of usable clamped into [2k, 15k], or config override
input.cfg.compaction?.preserve_recent_tokens ??
Math.min(MAX_PRESERVE_RECENT_TOKENS, Math.max(MIN_PRESERVE_RECENT_TOKENS, Math.floor(usable(input) * 0.25)))
// compaction.ts:228-233 — tail_turns <= 0 disables tail selection entirely
const limit = input.cfg.compaction?.tail_turns
if (limit !== undefined && limit <= 0) return { head: input.messages, tail_start_id: undefined }
...
const recent = limit === undefined ? all : all.slice(-limit)
// compaction.ts:237-261 — walk newest→oldest, keep while it fits, split the first non-fitter
for (let i = recent.length - 1; i >= 0; i--) {
  const size = yield* estimate({ messages: input.messages.slice(turn.start, turn.end), model })
  if (total + size <= budget) { total += size; keep = { start: turn.start, id: turn.id }; continue }
  const split = yield* splitTurn({...budget: remaining...})
  if (split) keep = split
  else if (!keep) yield* Effect.logInfo("tail fallback", ...)
  break                                                        // ONE oversize turn ends the walk
}
if (!keep || keep.start === 0) return { head: input.messages, tail_start_id: undefined }
```

**Flow:** `estimate` runs `MessageV2.toModelMessagesEffect` then `Token.estimate(JSON.stringify(msgs))` (:215-221) — cost stays proportional to the RETAINED tail because each candidate turn is estimated lazily inside the loop (:239 comment). When the newest fitting turn would still exceed the remaining budget, `splitTurn` scans forward INSIDE the failing turn for a start index whose suffix fits (:150-160), returning a mid-turn tail anchored at a message id. Selection result feeds `processCompaction`: everything before `keep.start` becomes the summarized `head`; `tail_start_id` is persisted onto the compaction part and re-checked/re-updated on repeat compactions (:461-466).
**Invariant:** The walk breaks after the FIRST turn that doesn't fit — older turns are never considered even if tiny (recency beats density). If nothing fits (`!keep`) the fallback keeps ALL messages (no tail cut); `keep.start === 0` also means "no head worth summarizing" ⇒ no compaction payload. Turn boundaries anchor on USER messages only; assistant-only prefixes belong to no turn and ride in the head.
**Probe:** `packages/opencode/test/session/compaction.test.ts` — `describe("session.compaction.process")` at :814 drives select through process; `PRUNE_PROTECT`/select constants pinned by grep:
```bash
grep -n 'PRESERVE_RECENT_TOKENS\|tail_turns\|tail_start_id' packages/opencode/src/session/compaction.ts | head
```
expect ≥6 hits including :32-33 constants and :461/:464 tail_start_id persistence.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "usable isOverflow", limit: 5 });
// resolves opencode.packages.opencode.src.session.overflow.usable (overflow.ts:10-20)
//     and ...overflow.isOverflow (overflow.ts:22-34)
```

## Verdict
Adopt the usable/reserved arithmetic and the recency-first budgeted tail walk verbatim; adapt Token.estimate to host tokenizer; omit SessionV1 schema specifics.
