<!-- capsule-v2 -->
# System-reminder smoosh — how are context injections attached to tool results without creating a second human turn?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does the engine guarantee every attachment-origin text block ends up INSIDE (or smooshed onto) a tool_result rather than sitting as standalone text that teaches the model to stop?

## ensureSystemReminderWrap + smooshSystemReminderSiblings
**Path/Symbol:** `src/utils/messages.ts:ensureSystemReminderWrap` (:1797-1817), `smooshSystemReminderSiblings` (:1835-1873), `wrapInSystemReminder` (:3097-3099), gate `tengu_chair_sermon` (:2273-2277, :2334-2338).
**Signature:** `(msg: UserMessage) => UserMessage` (idempotent wrap); `(messages: (UserMessage|AssistantMessage)[]) => (UserMessage|AssistantMessage)[]` (smoosh).
**Data Shape:** discriminator is the literal `<system-reminder>` PREFIX on text blocks — chosen so no per-collector code needs to remember wrapping ("no need for every normalizeAttachmentForAPI case to remember to wrap" :1789-1796).

### Decisive source
```ts
// Final pass: smoosh any `<system-reminder>`-prefixed text siblings into the
// last tool_result of the same user message. Catches siblings from:
// - PreToolUse hook additionalContext ... - any attachment-origin text that
//   escaped merge-time smoosh
// Non-system-reminder text (real user input, TOOL_REFERENCE_TURN_BOUNDARY,
// context-collapse `<collapsed>` summaries) stays untouched — a Human: boundary
// before actual user input is semantically correct.
if (b.type === 'text' && b.text.startsWith('<system-reminder>')) srText.push(b)
const lastTrIdx = kept.findLastIndex(b => b.type === 'tool_result')
const smooshed = smooshIntoToolResult(lastTr, srText)
if (smooshed === null) return msg // tool_ref constraint — leave alone
```

**Flow:** attachment messages → ensureSystemReminderWrap wraps ALL their text blocks at API-prep time → merge passes may leave wrapped text as siblings of a tool_result inside one user message → final gated pass folds every SR-prefixed sibling into the LAST tool_result positionally adjacent in the rendered prompt → non-SR text deliberately stays (A/B cited: real user input left as sibling + 2 SR-teachers removed → 0% regression). The smoosh runs AFTER an adjacent-user merge that exists SOLELY to feed it — both under the same gate because ungated merging changes VCR fixture hashes with no benefit when smoosh is off (:2327-2338).
**Invariant:** (1) the prefix is a CONTRACT across subsystems — anything emitting model-facing context text must start with `<system-reminder>` or it will be treated as user input and left as a turn boundary; (2) smoosh targets the LAST tool_result only; (3) idempotence both directions (wrap skips already-wrapped; smoosh on already-folded content no-ops) since query.ts re-runs this per tool round and output flows back through claude.ts next request; (4) `smooshIntoToolResult` returning null (tool_ref constraint) leaves the message untouched rather than corrupting it.
**Probe:** coverage caveat (no upstream tests). Deterministic probes: `sed -n '1819,1834p' src/utils/messages.ts` pins the catch-list comment verbatim; `grep -n "chair_sermon" src/utils/messages.ts` shows all three gate sites; graph resolves smooshSystemReminderSiblings :1835-1873 / ensureSystemReminderWrap :1797-1817 line-exact.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "smooshSystemReminderSiblings system reminder", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt prefix-discriminator + final-smoosh-pass for injecting context beside tool results; adapt the tag name; omit the A/B-gated toggles. Porting traps: wrapping REAL user input (the model then ignores genuine user turns as reminders); smooshing into a non-last tool_result breaks positional adjacency with the rendered prompt.
