<!-- capsule-v2 -->
# SAM agent turn hooks — how do you gate, meter, and rewind an in-app agent whose every turn can spend credits?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** How do beforeTurn/onStepFinish/onChatResponse/onRequest divide gating, metering, and race containment?

## Think-subclass lifecycle: gate → accumulate → meter → rewind
**Path/Symbol:** `src/server/features/sam/SamChatAgent.ts:beforeTurn` (:252-310), `onStepFinish` (:312-314), `onChatResponse` (:316-360), `onRequest` rewind (:374-409), `refusalTurn` (:248-250).
**Signature:** `class SamChatAgent extends Think` (one DO per chat session; DO instance name IS the session id, authorized in the Worker before connect).
**Data Shape:** Per-turn billing state `turnCostUsd`, `turnMonthlyRemaining`; context blocks "soul" + read-only "project_context" (no set provider ⇒ Think exposes no set-context tool; writes go through the update_project_context MCP tool); maxSteps 48, maxOutputTokens 6000.

### Decisive source
```ts
// Gates swap the model for one turn: the canned model streams the refusal back
// through Think's normal pipeline … without calling a provider, so a refusal is
// free even when users script them. The old version made a real 200-token call,
// which MiniMax M3 could spend entirely on reasoning tokens — leaving the user a
// truncated chain-of-thought and no reply (issue #161).
private refusalTurn(text: string): TurnConfig { return { model: staticAssistantModel(text) }; }
// rewind: Abort the turn and wait for it to settle BEFORE deleting, or its still-
// running loop keeps streaming chunks and persists a fresh assistant message right
// after the delete — an orphaned reply to nothing.
this.cancelAllChats(); await this.waitUntilStable({ timeout: 5000 });
```

**Flow:** beforeTurn resolves session/project once per DO lifetime → hosted mode confirms credit depletion via a SECOND Autumn read path before refusing (a stale check once locked a paying customer out) → returns tools (project-scoped MCP toolset) + limits OR a refusal TurnConfig → onStepFinish accumulates OpenRouter cost from providerMetadata → onChatResponse meters accumulated spend under the armed monthly-remaining, titles/touches the session, then refreshes system prompt so context written mid-turn is visible next turn → onRequest /rewind cancels in-flight turns, waits for stability, deletes message tail, clears stored terminal state.
**Invariant:** Refusals must not call the provider — swap in a canned model instead of generating text. Depletion confirmation uses a second read path before locking anyone out. Rewind MUST abort+settle before delete or the turn persists an orphaned reply after deletion. Context-block providers scope their own PG client (Think internals invoke them outside any ambient scope).
**Probe:** `src/server/features/sam/samChatTools.test.ts` (tool wiring); behavior pins via `grep -n "refusalTurn\|cancelAllChats" src/server/features/sam/SamChatAgent.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "SamChatAgent beforeTurn refusalTurn onChatResponse rewind", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: canned-model refusals, arm/accumulate/meter turn billing split across hooks, cancel-settle-delete rewind ordering, read-only context blocks with explicit write tools. Adapt the Think hook names to your agent framework. Omit the SAM persona/skill content.
