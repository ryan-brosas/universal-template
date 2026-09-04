<!-- capsule-v2 -->
# Goal inference + idle kickstart — how does /supervise with no args bootstrap a goal, and when is the agent nudged?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** What gates decide "there IS a goal to infer", how is the inferred outcome cleaned, and why does kickstart fire only on idle?

## inferOutcome (`src/core/inference.ts`) + command handler (`src/index.ts:405-460`)
**Path/Symbol:** `inference.ts:inferOutcome` (:34-77); `src/index.ts` handler no-args branch :407-460; kickstart condition also at :115-119 (model-initiated) and :499-503 (explicit goal).
**Signature:** `inferOutcome(ctx, provider, modelId, signal?): Promise<string | null>`.
**Data Shape:** Cleanup chain: strip leading/trailing quotes → newlines→spaces → trim → slice(0,200).

### Decisive source
```ts
const messages = extractMessages(ctx);
if (messages.length === 0) return null;
const summary = buildCompactionSummary(messages);      // SAME compaction pipeline
const contextText = formatForSupervisor(summary);
if (!contextText) return null;
// prompt: "extract the user's primary goal... Respond with ONLY the outcome statement."
const result = await session.prompt(userPrompt, signal);
session.dispose();                                     // throwaway session — different system prompt
return result.replace(/^["']|["']$/g, '').replace(/\n/g, ' ').trim().slice(0, 200);
```
Command-side gates: `hasConversation = !s?.active && hasUserMessages(ctx)` — no history or already-active ⇒ warn and return. API-key probe before starting: missing key for the resolved provider ⇒ interactive pickModel fallback. Kickstart: `if (ctx.isIdle()) pi.sendUserMessage('Please start working on this goal: <outcome>', {deliverAs:'followUp'})`.

**Flow:** no-args → require existing user messages → infer through the same normalize/filter/sections pipeline used for steering (structured context beats raw dump) → clean/slice → state.start → if the agent is IDLE inject a follow-up prompt so supervision starts actual work; a BUSY agent just gets watched until its next settle.
**Invariant:** (1) Kickstart is idle-conditional at ALL THREE entry points (command explicit, command inferred, model tool) — never queue work into a running turn. (2) Inference uses its own THROWAWAY session (goal-extraction system prompt differs from judge prompt); reusing the singleton would poison its memory. (3) Empty contextText ⇒ null ⇒ graceful warning rather than supervising toward nothing. (4) The cleanup chain guarantees single-line ≤200-char outcomes fit the widget header.
**Probe:** `tests/engine.test.ts` inferOutcome suite (:458-606) — `returns null when sessionManager has no branch entries`, `cleans up result: removes quotes, newlines, and limits length` (:531), `uses goal extraction system prompt` (:598); kickstart matrix in `tests/supervise-command.test.ts` (:186-362).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "inferOutcome hasUserMessages kickstart followUp isIdle", limit: 8 });
```

## Verdict
Adopt gated inference + idle-only kickstart + outcome sanitation for any auto-bootstrapping supervisor. Adapt the extraction prompt. Omit the API-key fallback if your host resolves credentials invisibly.
