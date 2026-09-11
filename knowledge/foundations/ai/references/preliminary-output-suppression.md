<!-- capsule-v2 -->
# Preliminary tool-output suppression in history conversion — when does a delivered tool output stay out of model history?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** Interrupted async-generator tools persist PRELIMINARY outputs marked `output-available` — how does `convertToModelMessages` stop replaying them as completed results?

## Preliminary flag gate
**Path/Symbol:** `packages/ai/src/ui/convert-to-model-messages.ts:66`.
**Signature:** membership predicate inside the tool-part filter: `(part.state === 'output-available' && part.preliminary !== true) || ...`.
**Data Shape:** UI tool parts carry `state`, optional `preliminary?: true`, and `output` shaped by the tool's `toModelOutput`.

### Decisive source
```ts
(part.state === 'output-available' && part.preliminary !== true) ||
```
(one-line gate replacing the previous bare `part.state === 'output-available' ||`)

**Flow:** history conversion walks assistant message parts; a part that is output-available BUT flagged preliminary is now EXCLUDED from the model-visible tool message entirely — the tool's `toModelOutput` is never invoked for it (test asserts call count 0) — so a resumed turn cannot treat "half finished" progress as a final answer; non-preliminary outputs pass unchanged.
**Invariant:** `preliminary === true` demotes an output to progress-only regardless of its state string; ignoring incomplete tool calls (`ignoreIncompleteToolCalls`) and this filter compose so interrupted streams leave NO fabricated tool result in history.
**Probe:** `convert-to-model-messages.test.ts` — "should ignore preliminary tool outputs" (asserts `toModelOutputCalls === 0` and the user-only message list); deterministic probe: `grep -cF "part.preliminary !== true" packages/ai/src/ui/convert-to-model-messages.ts` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "ignoreIncompleteToolCalls convertToModelMessages preliminary", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the flag-gated exclusion; adapt your own streaming-tool state union to carry an equivalent `preliminary` marker; omit nothing — without the flag, resumed agent turns confidently cite unfinished work as fact.
