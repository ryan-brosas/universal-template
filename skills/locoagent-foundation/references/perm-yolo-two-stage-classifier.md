<!-- capsule-v2 -->
# Two-stage XML classifier — fail-closed parse ladder, cache-pinned prefix, thinking-headroom trap

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you use an LLM as a security gate — transcript projection, prompt-cache economics across two stages, and what must happen when the model answers garbage?

## Path/Symbol
**Path/Symbol:** `src/utils/permissions/yoloClassifier.ts` — `buildTranscriptEntries` user-text + tool_use-only projection (:302-360), `toCompactBlock` JSONL/text formats with throw-fallback (:384-424), `buildYoloSystemPrompt` template REPLACE-vs-ADDITIVE (:484-540), `stripThinking`/`parseXmlBlock`/`parseXmlReason` (:567-604), `classifyYoloActionXml` two-stage ladder (:711-996), `classifyYoloAction` tool-use variant (:1012-1306), `getClassifierThinkingConfig` tuple (:683-693), `formatActionForClassifier` (:1487-1495).
**Signature:** `classifyYoloAction(messages, action: TranscriptEntry, tools, context, signal) → YoloClassifierResult {shouldBlock, reason, unavailable?, transcriptTooLong?, usage, stage…}`.
**Data Shape:** Transcript = user text blocks + assistant tool_use ONLY (assistant text excluded as attacker-controlled); each block serialized via the TOOL'S OWN `toAutoClassifierInput` projection; '' from that projection = "no security relevance" → auto-allow without an API call.

### Decisive source
```ts
// Models with alwaysOnThinking (declared in tengu_ant_model_override) default
// to adaptive thinking server-side and reject `disabled` with a 400. For those:
// don't pass `thinking: false`, instead pad max_tokens so adaptive thinking
// ...doesn't exhaust the budget before <block> is emitted. Without headroom,
// stop_reason=max_tokens yields an empty text response → parseXmlBlock('')
// → null → "unparseable" → safe commands blocked.
function getClassifierThinkingConfig(model: string): [false | undefined, number] {
  if (process.env.USER_TYPE === 'ant' && resolveAntModel(model)?.alwaysOnThinking) {
    return [undefined, 2048]
  }
  return [false, 0]
}
```

**Flow:** project messages (queued_command attachments become user turns) → build system prompt by replacing `<permissions_template>` with external OR anthropic template (external wraps defaults INSIDE `<user_*_to_replace>` tags so user values REPLACE them; anthropic keeps defaults outside with empty tag pairs so values are ADDITIVE — same substitution code, opposite semantics) → stage 1 "fast": max_tokens 64 + stop_sequences `</block>`, suffix "Err on the side of blocking. \<block\> immediately."; verdict `no` returns allow immediately → blocked/unparseable escalates to stage 2 "thinking" (max_tokens 4096, CoT suffix requiring EXPLICIT not suggestive user confirmation) → unparseable at ANY stage = shouldBlock:true ("blocking for safety"); API error = shouldBlock:true with `unavailable:true` so callers can apply their own iron-gate (fail-closed default, 30-min cached flag) or fail-open; "prompt is too long" is detected as deterministic (`transcriptTooLong`) and falls back to manual prompting instead of deny-retry-deny. Cache economics: one shared system block + AGENT.md prefix message + `cache_control` on the FINAL action block gives stage 2 a guaranteed hit on stage 1's full prefix (2-3 of 4 allowed breakpoints); classifier context must stay BELOW main-loop size so auto-compact fires first (ratio telemetry alerts p95 > 1.0).

**Invariant:** (1) Every non-answer is a block: no tool_use block, schema violation, XML parse failure, abort, or API error → `shouldBlock:true`; distinguish "actively blocked" from "couldn't respond" via `unavailable`. (2) Assistant-authored text never reaches the classifier transcript — only tool_use inputs (which are host-structured) and user text. (3) Hostile content cannot forge transcript lines: JSONL mode stringifies the whole line; text mode relies on JSON escaping keeping newlines inside string values. (4) Unvalidated historical tool input is thrown into fallback raw-object encoding rather than crashing the projection. (5) Thinking-capable models need max_tokens HEADROOM or empty responses masquerade as parse failures and block safe commands. (6) Denial tracking (3 consecutive / 20 total) falls back to human prompting, resetting on any success.

**Probe:** coverage caveat — no upstream unit tests reachable. Deterministic pins from repo root: `grep -nF 'Err on the side of blocking. <block> immediately.' src/utils/permissions/yoloClassifier.ts` → :550; `grep -nF 'strictly ADDITIVE' src/utils/permissions/yoloClassifier.ts` → :516; `grep -nF 'safe commands blocked' src/utils/permissions/yoloClassifier.ts` → :678; `grep -cF 'blocking for safety' src/utils/permissions/yoloClassifier.ts` → 5; graph search `classifyYoloAction` → yoloClassifier.ts :1012-1306 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "buildTranscriptEntries toCompactBlock classifyYoloActionXml parseXmlBlock", limit: 8 });
```

## Verdict
Adopt the fail-closed parse ladder, tool-owned input projection, single-template dual-replace semantics made explicit, two-stage cache-pinned prompting, and the too-long-is-deterministic classification. Adapt prompts/templates to your policy. Omit ant dump paths, Datadog field lists, and the POWERSHELL_DENY_GUIDANCE strings unless porting PS auto mode.
