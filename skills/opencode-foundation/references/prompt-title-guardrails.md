<!-- capsule-v2 -->
# Session title guardrails — when does the auto-title LLM call actually fire, and what gets cleaned?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How is the one-shot title generation gated so it never burns tokens on follow-ups, renames, or synthetic-only sessions?

## Four-gate one-shot titling
**Path/Symbol:** `packages/opencode/src/session/prompt.ts` (`title`, lines 193–253; forked at :1133–1139).
**Signature:** `title({session, history, providerID, modelID}): Effect<void>` — `Effect.ignore` + `forkIn(scope)` from loop step 1.
**Data Shape:** Gates: (1) `session.parentID` set ⇒ never (children don't title); (2) `!Session.isDefaultTitle(session.title)` ⇒ never (user/fork renamed already); (3) exactly ONE "real" user message in history (`role==="user"` AND NOT all parts `synthetic`) — `findIndex` must equal the count filter; (4) a "title" agent must exist. Model ladder: title-agent's model → `provider.getSmallModel(current provider)` → current model. Subtask-only first messages collapse to their prompts joined by "\n".

### Decisive source
```ts
// prompt.ts:199-217 — every gate must pass or the call is skipped entirely
if (input.session.parentID) return
if (!Session.isDefaultTitle(input.session.title)) return
const real = (m: SessionV1.WithParts) =>
  m.info.role === "user" && !m.parts.every((p) => "synthetic" in p && p.synthetic)
const idx = input.history.findIndex(real)
if (idx === -1) return
if (input.history.filter(real).length !== 1) return   // second real user msg ⇒ window closed forever
...
const msgs = onlySubtasks
  ? [{ role: "user", content: subtasks.map((p) => p.prompt).join("\n") }]
  : yield* MessageV2.toModelMessagesEffect(context, mdl)
```

**Flow:** step 1 of runLoop forks title in background → gates → stream with `system: []`, `tools: {}`, `small: true`, `retries: 2`, prompt "Generate a title for this conversation:" → strip `<think>...</think>` blocks → take first non-empty trimmed LINE → clamp >100 chars to 97+"..." → `sessions.setTitle`, swallowing failure via logError.
**Invariant:** Titling is at-most-once per session and decided by message CONTENT, not a flag: any subsequent real user message makes the count-filter fail forever. The `<think>` strip handles reasoning models that leak CoT into the first line; without it titles start with chain-of-thought. Failures are logged, never surfaced.
**Probe:** exercised indirectly by every `prompt.prompt` integration test (title fiber runs on step 1); direct gate coverage lives in session.test.ts default-title handling — treat exact line-clamp/think-strip as source-pinned only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", qn_pattern: "packages.opencode.src.session.prompt", limit: 20, detail: "ids" });
```

## Verdict
Adopt the four gates + think-strip + 100-char clamp; adapt agent/model resolution to host naming; omit the literal title prompt wording.
