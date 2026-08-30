<!-- capsule-v2 -->
# Gemini header-runaway interrupt + post-prompt recovery — how do you abort a runaway reasoning stream mid-flight and repair the context afterwards without losing the turn?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** What is the full detect→abort→wait→discard→remind→continue choreography, and why must the reminder run as a generation-guarded post-prompt task instead of inline?

## LoopGuards Gemini recovery choreography
**Path/Symbol:** `packages/coding-agent/src/session/stream-guards.ts:` `LoopGuards` (352–498); detection `onAssistantEvent` (:373–385), recovery `#interruptGeminiHeaderRunaway` (:450–497), settings gate `#geminiHeaderGuardActive` (:439–448).
**Signature:** `class LoopGuards { recordTurn(messages: AgentMessage[], context?: AgentTurnEndContext): void; onAssistantEvent(message: AssistantMessage, event: AssistantMessageEvent): void }`.
**Data Shape:** `GeminiHeaderRunDetector.push(delta): boolean` (fires when repeated planning headers exceed threshold; `.count` = header count); reminder CustomMessage `{role:"custom", customType:"gemini-tool-call-reminder", display:false, details:{headers}, attribution:"agent"}`.

### Decisive source
```ts
this.#host.agent.abort(GEMINI_HEADER_INTERRUPT_REASON);
const generation = this.#host.promptGeneration();
this.#host.schedulePostPromptTask(async signal => {
	if (signal.aborted || this.#host.isDisposed() || this.#host.promptGeneration() !== generation) return;
	await this.#host.agent.waitForIdle();
	if (signal.aborted || this.#host.isDisposed() || this.#host.promptGeneration() !== generation) return;
	const aborted = this.#host.agent.state.messages.findLast(
		(message): message is AssistantMessage =>
			message.role === "assistant" && message.timestamp === targetTimestamp,
	);
	if (aborted) this.#host.discardAssistantTurn(aborted);
	// ... render + append gemini-tool-call-reminder custom message ...
	await this.#host.agent.continue();
});
```

**Flow:** `thinking_start` → detector instantiated only when guard active (`model.loopGuard.enabled` AND `model.loopGuard.toolCallReminder` AND `PI_NO_THINKING_LOOP_GUARD !== "1"` AND `modelFamilyToken(model.id) === "gemini"`) → `thinking_delta` pushes text; on trigger → immediate `agent.abort(reason)` mid-stream → schedule post-prompt task snapshotting `promptGeneration()` → re-check generation AFTER `waitForIdle()` → locate the aborted turn by exact timestamp match via `findLast` → discard it → append hidden reminder custom message to agent AND session entries → `agent.continue()`. `text_start`/`toolcall_start` reset the detector.
**Invariant:** The generation captured at abort time is checked twice — before and after the async idle wait — because any new prompt invalidates the recovery; discarding a turn from a newer prompt would corrupt context. Turn identity is the message timestamp (not index), stable across the abort's mutations. Cross-turn tool loops use the same class but a different path: `recordTurn` detects repeats and injects a redirect message into BOTH the in-memory array and session persistence.
**Probe:** `test/agent-session-empty-stop-guard.test.ts` covers adjacent empty-stop recovery; the guard's settings gates are pinned by grep: `grep -c 'modelFamilyToken(model.id) === "gemini"' src/session/stream-guards.ts` → 1 at pin 4854db85 (executed green).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "LoopGuards GeminiHeaderRunDetector tool call loop redirect", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: `LoopGuards.#injectToolCallLoopRedirect stream-guards.ts:405-437`, `.#activeToolCallLoopGuard :387-403`.

## Verdict
Adopt the two-phase generation-guarded recovery and timestamp-based turn location. Adapt the detector threshold/model-family gate to your host's model identity scheme. Omit the Gemini-specific header vocabulary if porting to a non-Gemini host — the choreography (abort now, repair after idle, continue) is the portable part. Runner caveat: bun test blocked by pi-natives build in this environment; probe verified byte-exact by grep.
