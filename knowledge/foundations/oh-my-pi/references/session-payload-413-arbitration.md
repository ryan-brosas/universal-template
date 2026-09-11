<!-- capsule-v2 -->
# Payload-413 arbitration — how do you tell an HTTP 413 byte/media rejection apart from a token-context overflow, and route each to the recovery it can actually fix?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** What is the classification + arbitration ladder (flags, usage evidence, local occupancy gauge, ambiguity rules) that decides between skip-compaction, fallback chain, and dead-end for a 413?

## Payload-rejection arbitration funnel
**Path/Symbol:** `packages/ai/src/error/flags.ts:` `isPayloadRejection` (:790–795), `isUsageBackedContextOverflow` (:776–780), `isTextAmbiguousContextOverflow` (:800–810), two-phase finalization in `classifyMessage` (:749–757); arbitration `packages/coding-agent/src/session/session-maintenance.ts` (:1775–1836, ceiling constant :205); model-swap veto `session/turn-recovery.ts:1725-1726`.
**Signature:** `isPayloadRejection(message): boolean; isUsageBackedContextOverflow(message, contextWindow?): boolean; isTextAmbiguousContextOverflow(errorId, message?, contextWindow?): boolean`.
**Data Shape:** Bitflag errorId (`Flag.PayloadRejected`, `Flag.ContextOverflow`); trusted gate inputs = reported input tokens (usage.input+cacheRead+cacheWrite), stored-token estimate, contextWindow; `PAYLOAD_REJECTION_OCCUPANCY_CEILING = 0.9`.

### Decisive source
```ts
const payloadRejection =
	sameModel && !errorIsFromBeforeCompaction && AIError.isPayloadRejection(assistantMessage);
const ambiguousPayloadRejection =
	payloadRejection && AIError.is(assistantMessage.errorId, AIError.Flag.ContextOverflow);
const storedTokens = payloadRejection && contextWindow > 0 ? this.#estimateStoredContextTokens() : 0;
const trustedPayloadRejection =
	payloadRejection &&
	contextWindow > 0 &&
	reportedInputTokens <= contextWindow &&
	storedTokens < contextWindow * PAYLOAD_REJECTION_OCCUPANCY_CEILING;
if ((payloadRejection && !ambiguousPayloadRejection && contextWindow <= 0) || trustedPayloadRejection) {
	// remove from active context, emit "this is NOT a token-context problem" notice,
	// BLOCK automatic continuation — compaction cannot shrink bytes or image budgets.
```

**Flow:** provider 413 → `classifyMessage` merges status-inferred flags with text classification; two-phase finalization DROPS the stale PayloadRejected bit when final text proves token overflow → maintenance checks same-model + not-pre-compaction → TRUSTED payload rejection (local gauge shows ≤90% occupancy and usage agrees) ⇒ skip compaction entirely, block auto-continuation with a remedies notice (drop archived image frames / raise body limit / switch compaction.methodOrder away from snapcompact) → UNTRUSTED (gauge shows no headroom) ⇒ fall through to normal overflow recovery (context promotion, then compaction) → dual-flag bare-413s (PayloadRejected+ContextOverflow without usage proof) consult the configured model fallback chain because another provider's larger byte budget may accept the request → usage-backed overflows are AUTHORITATIVE window excesses: never routed to chains, reported honestly as token-context dead ends.
**Invariant:** Compaction only shrinks TOKENS, never BYTES or media budgets — routing a true payload rejection into token compaction produces an infinite retry loop. Usage evidence always outranks response bodies ("believes provider-reported usage when it contradicts a payload-only body"). The model-swap veto in turn-recovery (:1726 `if (AIError.isPayloadRejection(message)) return false`) stops base→fallback model swaps from "fixing" a 413 that will fail identically (#9235). Stale-error guards: foreign-model errors and errors predating the latest compaction entry never trigger anything.
**Probe:** `test/agent-session-payload-rejection-413.test.ts` — 19 scenario tests pinning every rung incl. `"honestly skips token compaction for a low-token payload-shaped 413"` :239, `"believes provider-reported usage when it contradicts a payload-only body"` :696, `"blocks dual-flag bare-413 dead ends even though overflow evidence is present"` :792; veto verified byte-exact at pin: `grep -cF 'AIError.isPayloadRejection(message)' src/session/turn-recovery.ts` → 1 (executed green).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "isPayloadRejection trustedPayloadRejection payload rejection compaction", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: `isPayloadRejection flags.ts:790-795`, test helpers `payloadRejectionAssistant agent-session-payload-rejection-413.test.ts:146-167`.

## Verdict
Adopt the flag taxonomy, the trusted-gate arithmetic (occupancy ceiling), the ambiguity rule (dual-flag w/o usage proof ⇒ try fallback chains), and honest usage-backed dead-end reporting. Adapt notice wording and settings keys. Omit provider-specific 413 body regexes (data packs behind `matchesPayloadRejectionText`).
