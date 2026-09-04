<!-- capsule-v2 -->
# OpenCode bridge usage accounting — how do you compute honest per-turn usage from a runtime that reports cumulative session totals and per-step tokens in different shapes?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** The runtime's session object carries CUMULATIVE token counters (and they can reset mid-session), while each step event carries its own token block in yet another shape. Which number is the turn's usage, and how do you keep both paths from lying?

## Session-delta primary, step-accumulation fallback
**Path/Symbol:** `packages/harness-opencode/src/bridge/opencode-usage.ts` — `mapUsage` (:18–34), `extractSessionTokens` (:40–51), `subtractSessionTokens` (:53–69), `addUsage` (:71–105), `numberValue` (:139–141), `diff` (:143–145), `add` (:147–159); `packages/harness-opencode/src/bridge/index.ts` — `runPrompt` token capture (:578–581, :647–650, :749–760).
**Signature:** `mapUsage(tokens: unknown): HarnessUsage`; `subtractSessionTokens({before, after}: {before: OpenCodeTokenUsage; after: OpenCodeTokenUsage}): OpenCodeTokenUsage`; `addUsage({left, right}): HarnessUsage`.
**Data Shape:** runtime tokens = `{input, output, reasoning, cache:{read, write}}`; harness usage = V4 nested `{inputTokens:{total,noCache,cacheRead,cacheWrite}, outputTokens:{total,text,reasoning}}`; session envelopes walked at four depths: `tokens`, `info.tokens`, `data.tokens`, `data.data.tokens`.

### Decisive source
```ts
// opencode-usage.ts:18–34 — flattening with a clamped noCache split
export function mapUsage(tokens: unknown): HarnessUsage {
  const value = extractOpenCodeTokens(tokens) ?? zeroOpenCodeTokens();
  const cacheRead = value.cache.read;
  return {
    inputTokens: {
      total: value.input,
      noCache: Math.max(0, value.input - cacheRead),
      cacheRead,
      cacheWrite: value.cache.write,
    },
    outputTokens: {
      total: value.output + value.reasoning,
      text: value.output,
      reasoning: value.reasoning,
    },
  };
}
```
```ts
// opencode-usage.ts:143–145 + index.ts:749–760 — clamped diff; delta path wins,
// accumulated finish-step usage is only the fallback
function diff({ before, after }: { before: number; after: number }): number {
  return Math.max(0, after - before);
}
// ...
const finalSessionTokens =
  (await readSessionTokens({ client, sessionId }).catch(() => undefined)) ??
  latestSessionTokens;
if (initialSessionTokens && finalSessionTokens) {
  return mapUsage(subtractSessionTokens({ before: initialSessionTokens, after: finalSessionTokens }));
}
return stepUsage;
```

**Flow:** BEFORE the prompt, `initialSessionTokens` is read (failure ⇒ undefined, never fatal) and every `session.updated` event refreshes `latestSessionTokens` via `extractSessionTokens` → at settlement, the final read falls back to the last event-captured value → when BOTH endpoints exist, per-turn usage = `mapUsage(subtractSessionTokens(before, after))` with every field clamped to `max(0, after-before)` so a mid-session counter reset yields zero for that field instead of a negative; otherwise the turn's usage is `stepUsage`, accumulated by `addUsage` over every emitted finish-step's usage (undefined-safe: both-null fields stay undefined, one-null adds against 0). `extractSessionTokens` requires the `cache` object to be present — a malformed envelope returns undefined rather than a half-zeroed record. Non-finite numbers coerce to 0 (`numberValue`).
**Invariant:** reported per-turn usage is never negative and never double-counted (exactly one of the two paths runs); a missing or malformed endpoint degrades to the other path or to zeros — it never throws out of the usage computation.
**Probe:** `packages/harness-opencode/src/bridge/opencode-usage.test.ts` (66L, 3 cases): extraction from all four envelope depths; malformed envelopes rejected (null/array/string-data/missing-cache ⇒ undefined); delta mapping (input 100→130 / output 40→400 / reasoning 5→25 / cache 80→100+10→12 ⇒ noCache 10, cacheRead 20, output total 380 text 360 reasoning 20). `packages/harness-opencode/src/bridge/opencode-finish-step.test.ts` (53L, 3 cases): legacy step-finish part → finish-step event with mapped usage + cost metadata; non-step-finish parts ignored; finish-reason normalization (length/tool_call/error/unknown).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "mapUsage subtractSessionTokens addUsage extractSessionTokens initialSessionTokens", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-path design (cumulative-counter delta as primary, per-event accumulation as fallback) whenever your runtime exposes both session-level counters and per-step usage; adopt per-field clamping for any cumulative counter that may reset; adopt envelope-walk extraction with a required-shape gate (malformed ⇒ undefined, never half-parsed); adopt undefined-safe addition so absent sub-counters can't poison totals. Adapt the field names, the envelope depths, and which path is primary to your runtime's guarantees; omit the event-captured fallback (`latestSessionTokens`) if your final read is reliable. Caveat: the runPrompt wiring (before-read, event refresh, final read) is deterministic-read-only; the kernel functions are fully test-pinned.
