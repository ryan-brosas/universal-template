<!-- capsule-v2 -->
# Prewalk arm command surface — how does a slash command arm a next-turn harness without double-firing?

**Source:** pi-fabric (MIT), `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** How do you arm a "do X on my next matching prompt" feature from a CLI command, exactly once, with the task delivered as a real user message?

## Prewalk arm command surface
**Path/Symbol:** `src/commands/fabric.ts:registerFabricCommand.handler` prewalk branch (:241–316); model picker `resolvePrewalkModel` :68–105; reload choreography :221–229.
**Signature:** handler splits arguments on `\s+`, defaults subcommand to `"dashboard"`; arm payload `{model, mode, sessionId, task?, thinking?, alwaysRearm}`.
**Data Shape:** hidden advisory message `{customType: PREWALK_ARMED_MESSAGE_TYPE, content: armedPrompt, display: false, details: {mode, model}}` sent `{deliverAs: "nextTurn"}`.

### Decisive source
```ts
// Hidden advisory framing, queued for the next prompt (rules before
// the task when one is submitted below). nextTurn never triggers a
// turn; custom messages never fire `input`, so observeTask ignores it.
const armedPrompt = prewalkArmedPrompt(state.config.prewalk.mode, model);
if (!hasPrewalkArmedPrompt(context.sessionManager.getBranch(), armedPrompt)) {
    pi.sendMessage({...}, { deliverAs: "nextTurn" });
}
...
if (task) pi.sendUserMessage(task);   // task submitted AFTER the advisory lands in queue
```

**Flow:** gate ladder FIRST — requires fullCodeMode ∧ schema.mode ≠ "enforce" (loud error otherwise), trajectory mode additionally requires agents.enabled → resolve model (config `provider/model` form validated by the `/` check; else sorted interactive picker from modelRegistry; non-interactive without config = error) → `state.prewalk.arm(...)` → deduplicated hidden advisory queued nextTurn (BEFORE the task) → inline task forwarded via sendUserMessage so it triggers the turn naturally. `--off`/`--cancel` and `--status` short-circuit before all gates.
**Invariant:** The identical armed prompt is NEVER re-queued when one already persists on the branch (`hasPrewalkArmedPrompt` dedup against the session branch) — re-arming updates controller state but not message spam; ordering matters: advisory sendMessage precedes task sendUserMessage (pinned via invocationCallOrder); `/fabric reload` choreography is stop UI → suspendToolCapture → state.initialize → applyFabricMode → start UI.
**Probe:** `tests/fabric-command.test.ts` ("skips the armed prompt when the identical one already persists" → sendMessage NOT called); grep -c 'deliverAs: "nextTurn"' src/commands/fabric.ts → 1.
**Anchor:** repo root.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "registerFabricCommand prewalk arm handler subcommands", limit: 10 });
// registerFabricCommand Function src/commands/fabric.ts 107-706
```

## Verdict
Adopt the dedup-then-queue-then-submit pattern for any next-turn arming UX; adapt the advisory envelope to your host's custom-message API; omit the id-based autocomplete machinery unless porting the whole command surface.
