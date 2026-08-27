<!-- capsule-v2 -->
# Compress-retry circuit breaker — when the model's compression ATTEMPT fails, how do you re-prompt without looping?

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** The nudge told the model to compress, it called compress, and the call FAILED (bad args / invalid ranges / all-noop) — what contract gets compression unstuck without an infinite retry loop?

## Turn-scoped outcome ledger with cap, dedup, and a two-sided suppression
**Path/Symbol:** `src/runtime.ts`: `MAX_COMPRESS_ATTEMPTS = 3` (:239), state trio (:289-291), `noteCompressOutcomes` (:293-316), `compressRetryCappedFor` (:318-320), `clearCompressRetryTracking` (:322-326); collection + injection `src/index.ts`: `collectCompressOutcomes` (:536-547), `turnStartIndex` (:524-529), retry block (:345-358), `compressRetryMessage` builder (:549-567); kernel-side filter `viableRanges` applied at :318.
**Signature:** `noteCompressOutcomes(turnKey, outcomes: { toolCallId, isError, success, noop? }[]): { count, retryFor: string | null, cappedNow }`.
**Data Shape:** outcomes come ONLY from the current user turn (`turnStartIndex` finds the last user entry; everything strictly after is "current turn"); classification per result: isError OR noop → failure (count++), success panel → reset to 0, other non-error text → neutral (frozen).
### Decisive source
```ts
// runtime.ts:309-315 — newest-outcome retry selection with double defense:
const latest = outcomes.length > 0 ? outcomes[outcomes.length - 1] : undefined;
// count >= 1 guards against a deduped stale failure sliding in with a
// reset-to-0 counter ("an 'attempt 0 of 3' prompt must be impossible")
const retryFor = latest && (latest.isError || latest.noop === true)
  && compressFailCount >= 1 && compressFailCount < MAX_COMPRESS_ATTEMPTS
  ? latest.toolCallId : null;
const cappedNow = compressFailCount >= MAX_COMPRESS_ATTEMPTS && prevCount < MAX_COMPRESS_ATTEMPTS;
```
**Flow:** why this exists — a failed compress consumed the turn's nudge budget while compressing nothing; the growth-gated nudge then stays silent and "the model often just continues" (session 01a00a38: one validation failure at 11:41Z, then 95 minutes of nudge silence). So on every context event: collect this turn's compress toolResults → note them (dedup via `compressOutcomeSeen` Set keyed by toolCallId — pi fires context events multiple times per reply) → if the NEWEST outcome is a failure and count < 3, append `compressRetryMessage(failed.text, count, 3)`: quote only the error lines BEFORE pi's `\n\nReceived arguments:` dump (capped 600 chars), show the correct array-shaped example, and on the final allowed attempt say so explicitly. Once count hits 3, `compressRetryCappedFor(turnKey)` also suppresses the (dedup-exempt) emergency NUDGE itself — but "the kernel's emergency truncation still shrinks context mechanically," so the breaker stops prompt loops, not safety. Success resets; a new user turn resets (turnKey changes); neutral outcomes freeze so mixed failure modes cannot bypass the cap.
**Invariant:** (1) Turn scoping is load-bearing BOTH ways: whole-session feeding would keep an old failure as newest-forever and re-prompt it at count 0 on every later turn; the caller MUST pre-scope (documented review finding on 7ddd2c6). (2) Process the outcome ledger BEFORE the nudge block so a same-fire success lifts the cap on that fire. (3) The nudge's own range list must be filtered through `viableRanges` first (:318) — "a tiny fragmented range in the list makes batched attempts fail atomically (kernel validates the whole batch)", i.e. bad recommendations CREATE the failures this breaker mops up. (4) Retry prompts are user-role synthetic messages rebuilt every context event — one-shot appends would vanish because pi rebuilds context per LLM call.
**Probe:** `cd /mnt/hdd/utopia/inspo/billion-context-pi && npx tsx --test tests/compress-retry.test.ts` — 10/10 GREEN at pin 6a88c556 (executed pass 12; outcome classification incl. noop-vs-error, per-turn reset, cap reachability, stale-failure immunity, issue-#6 loop breaker).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "noteCompressOutcomes collectCompressOutcomes compressRetryMessage MAX_COMPRESS_ATTEMPTS", limit: 10 });
```

## Verdict
Adopt the turn-scoped ledger, toolCallId dedup, newest-failure selection with the count≥1 guard, the capped suppression pairing (retry prompts AND nudge), and the error-quote truncation before argument dumps. Adapt the trigger tool name and message voice. Do not generalize the ledger across turns — cross-turn memory here is precisely the bug class the design forbids.
