<!-- capsule-v2 -->
# Pi dangling-host-tool rerun barrier — how do you resume a journal that ends with host tool calls still awaiting results, without racing the framework's re-delivery?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** When a cross-process resume restores a session journal whose last assistant message contains host tool calls with no results (the previous process died while blocked on host input), how do you make the framework's re-delivered results reach the model instead of being dropped or synthesized away?

## The hold-the-rerun-until-delivered barrier
**Path/Symbol:** `packages/harness-pi/src/pi-session.ts` — `findDanglingHostToolCalls` (:634–688), `acceptDanglingHostToolResult` (:690–716), `appendDeliveredHostToolResults` (:718–764), `deferRerunUntilHostToolResults` (:766–847), `doContinueTurn` branch (:1355–1375), inferred-step emission (:1140–1167).
**Signature:** `deferRerunUntilHostToolResults(danglingCalls, continueOpts): HarnessV1PromptControl` — returns a control whose `done` resolves only when every dangling call's result has arrived and the rerun completes.
**Data Shape:** `deliveredDanglingResults: Map<toolCallId, {toolName, output, isError}>`; the barrier `{awaiting: Map<toolCallId, toolName>, startRerun, cancel}`; the restored journal opened via `SessionManager.open(resumeSessionFilePath, hostSessionDir, sessionWorkDir)`.

### Decisive source
```ts
// pi-session.ts:634–688 (abridged) — what counts as dangling
const resolvedToolCallIds = new Set<string>(deliveredDanglingResults.keys());
for (const message of messages) {
  if (message.role === 'toolResult') resolvedToolCallIds.add(message.toolCallId);
}
for (const message of messages) {
  if (message.role !== 'assistant') continue;
  /* Pi's message transform drops errored/aborted assistant messages from the
   * LLM context entirely, so their tool calls are not awaiting results — the
   * model retries from the last valid state instead. */
  if (message.stopReason === 'error' || message.stopReason === 'aborted') continue;
  for (const block of message.content) {
    if (block.type === 'toolCall' && hostToolNames.has(block.name)
        && !resolvedToolCallIds.has(block.id)) {
      dangling.push({ toolCallId: block.id, toolName: block.name });
    }
  }
}
```
```ts
// pi-session.ts:718–764 (abridged) — delivered results are written INTO the
// restored journal before the rerun rebuilds the session from it
for (const [toolCallId, delivered] of deliveredDanglingResults) {
  journal.appendMessage({ role: 'toolResult', toolCallId, toolName: delivered.toolName,
    content: [{ type: 'text', text: serializeToolOutput(delivered.output) }],
    isError: delivered.isError, timestamp: Date.now() });
}
deliveredDanglingResults.clear();
```

**Flow:** doContinueTurn with no live turn scans the restored journal for dangling host-tool calls → if any, install the barrier and return a control WITHOUT starting the rerun → the framework re-delivers each result via `submitToolResult`; `acceptDanglingHostToolResult` stashes it and releases the rerun when the awaiting map empties → `appendDeliveredHostToolResults` writes the stashed results into the journal (serialized exactly as a live turn would produce them — otherwise Pi's message transform synthesizes "No result provided" error results) → runTurn rebuilds the session from the modified journal and emits a synthetic `finish-step {unified:'tool-calls', harnessMetadata:{pi:{inferredStep:true}}}` because the rerun has no live tool event to close the resumed step → suspend/stop also flush already-delivered results into the journal (the framework will never re-deliver them).
**Invariant:** the rerun NEVER starts before every dangling call has its real result (starting eagerly would resolve the calls as synthetic empty results and drop the submissions); ids already delivered by a PREVIOUS continuation count as resolved — re-awaiting them would deadlock the turn; errored/aborted assistant messages are excluded from the scan because Pi drops them from LLM context; a caller that resumes without supplying all continuations leaves the turn parked awaiting host input (same behavior as the in-process path); the injected step boundary is mandatory — without it the continuation layer mistakes the next assistant response for the resumed step and discards it.
**Probe:** `packages/harness-pi/src/pi-session.test.ts` :642–723 ("holds a cross-process rerun until dangling host tool results arrive, then injects them into the journal" — pins prompt-not-called-before-delivery, the appended toolResult bytes, and the inferredStep finish-step as the second emitted part), :724–782 (error flag preserved on injection), :783–824 (immediate rerun when nothing dangles), :825–900 (no re-await of previously delivered results), :901–961 (results delivered before a suspend flushed into the journal), :962–1041 (deferred-rerun cancel/abort/attach cases), :1042–1155 ("replays an approved host tool through HarnessAgent before rerunning Pi").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "findDanglingHostToolCalls deferRerunUntilHostToolResults appendDeliveredHostToolResults inferredStep", limit: 10 });
```

## Verdict
Adopt the barrier pattern for ANY journal-based rerun dialect where host-executed tools can be pending at process death: scan-for-dangling → hold → collect re-deliveries → inject-into-journal-before-rebuild → synthesize the missing step boundary. Adapt the "resolved" set to your own continuation bookkeeping; omit it entirely for bridge-backed dialects (their replay log carries the pending state losslessly — this hazard exists only because rerun recomputes). Coverage caveat: none — the whole family is test-pinned.
