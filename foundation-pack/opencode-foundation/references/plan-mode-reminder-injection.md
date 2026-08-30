<!-- capsule-v2 -->
# Plan-mode reminder injection — how do mode switches and plan files become synthetic user parts?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How are plan→build handoffs and plan-file existence communicated to the model without polluting real user input?

## Last-user-message mutation per loop step
**Path/Symbol:** `packages/opencode/src/session/reminders.ts` (whole file, 92L; called from prompt.ts:1180–1184 BEFORE the assistant shell is built).
**Signature:** `SessionReminders.apply({messages, agent, session}): Effect<WithParts[]>` — mutates `findLast(user).parts` and returns the same array.
**Data Shape:** Two regimes split by `flags.experimentalPlanMode`. Legacy: agent==="plan" ⇒ append `PROMPT_PLAN` text; prior plan-assistant present AND now building ⇒ append `PROMPT_BUILD_SWITCH`. Experimental: leaving plan mode checks the session's plan file (`Session.plan(session, ctx)`) and appends BUILD_SWITCH + (if exists) "A plan file exists at ${plan}. You should execute on the plan defined within it"; entering plan mode appends PLAN_MODE with `${planInfo}` substituted by create-vs-read guidance, creating the plan dir when missing.
**Decisive source:**
```ts
// reminders.ts:37-47 — legacy switch fires on HISTORY, not flags
const wasPlan = input.messages.some((msg) => msg.info.role === "assistant" && msg.info.agent === "plan")
if (wasPlan && input.agent.name === "build") {
  userMessage.parts.push({ ... type: "text", text: BUILD_SWITCH, synthetic: true })
}
// reminders.ts:70 — re-entering plan while ALREADY planning is a no-op
if (input.agent.name !== "plan" || assistantMessage?.info.agent === "plan") return input.messages
```

**Flow:** every loop iteration after compaction check → find last user message → branch on flag regime and current/previous agent names → push synthetic part(s) → the SAME array flows into `MessageV2.toModelMessagesEffect`, so reminders ride the next LLM request exactly once per step they're appended.
**Invariant:** Reminders are APPENDED each relevant step (idempotence comes from the wasPlan/agent guards, not dedup) and are ALWAYS `synthetic: true` so title generation's `real`-message filter and history replay ignore them. The experimental variant PERSISTS its part via updatePart (survives reload) while legacy parts are ephemeral in-memory additions to the message object.
**Probe:** `packages/opencode/test/session/instruction.test.ts` covers instruction sibling plane; reminder behavior pinned indirectly via plan-mode integration tests (`test/agent/plan-mode-subagent-bypass.test.ts`) — direct unit coverage for apply() is thin; treat legacy/experimental branch conditions as source-pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "reminders plan mode synthetic", limit: 8 });
```

## Verdict
Adopt synthetic-part injection with history-derived switching and persisted-vs-ephemeral duality; adapt plan-file path derivation; omit literal prompt texts (product surface).
