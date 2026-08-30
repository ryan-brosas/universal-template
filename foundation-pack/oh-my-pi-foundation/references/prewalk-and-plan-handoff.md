<!-- capsule-v2 -->
# Prewalk — plan first, hand off only after a durable implementation boundary

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory project `oh-my-pi`. **Path:** `packages/coding-agent/src/session/prewalk.ts`. **Question:** How do you move from planning to implementation without switching on read-only exploration or losing hidden plan state?

## Source contract
**Path/Symbol:** `prewalk.ts:PrewalkCoordinator.advanceAtTurnEnd` (138–204), `isPrewalkImplementationAction` (43–53), `#finalizePlanYoloProposal` (284–…), host seam `waitForSessionMessagePersistence` (80).
**Signature:** `advanceAtTurnEnd(liveMessages, context): Promise<void>`; implementation classifier accepts a completed `ToolResultMessage`.
**Data Shape:** target model, todo-gate state, hidden custom plan nudge (`PREWALK_PLAN_MESSAGE_TYPE`, `display: false`), completed tool results, persisted session messages.

### Decisive source
```ts
const action = todoGateOpen ? context.toolResults.find(result => isPrewalkImplementationAction(result)) : undefined;
if (!action) {
  this.#host.agent.steer({ customType: PREWALK_PLAN_MESSAGE_TYPE, content: prewalkPlanPrompt, display: false });
  return;
}
await this.#host.waitForSessionMessagePersistence(context.message);
await this.#host.setModelTemporary(target, prewalk.thinkingLevel, { ephemeral: true });
```

**Flow:** inject hidden plan prompt → wait for todo if available → classify the first genuine mutation → persist session context (`waitForSessionMessagePersistence` for BOTH the user message and its tool result) → scrub hidden nudge → switch model at the next safe boundary (ephemeral setting) → inject implementation checklist.

**Invariant:** a `write`/device result with `tier: "read"` is exploration, not implementation; plan nudges never survive a context rebuild — persistence precedes every mode flip.

**Probe:** direct `test/agent-session-prewalk.test.ts:118–217` waits for the first post-todo write; `:407–525` rejects read-tier device dispatch but accepts write-tier dispatch. Coverage caveat: tests excluded from graph index by design.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "PrewalkCoordinator advanceAtTurnEnd implementation action", limit: 12, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.coding-agent.src.session.prewalk.isPrewalkImplementationAction" });
```

## Verdict
Adopt turn-end plan gating with persistence-before-switch and tier-aware mutation classification; adapt message types and model-switch mechanics to host; omit the YOLO-proposal UI unless porting the full planning UX.
