<!-- capsule-v2 -->
# Workflow-harness durable step engine — how do you drive one long agent turn across workflow step boundaries so each execution is resumable and the UI stream stays coherent?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** When a durable workflow runtime re-executes a step from a persisted checkpoint, what state shape and stream discipline let a harness agent turn survive slice boundaries, approval pauses, and process death without duplicating or losing UI chunks?

## One serializable state, two cursors, one terminal finish
**Path/Symbol:** `packages/workflow-harness/src/run-harness-agent.ts` — `runHarnessAgent` (:99–338), `writeRequiredPrelude` (:379–405), `recordWorkflowChunk` (:409–461), `closeOpenExecutionParts` (:463–480), `hasPendingHostInput` (:502–505), `toResumeState` (:509–517); `packages/workflow-harness/src/harness-workflow-state.ts` — `HarnessWorkflowState` (:71–106), status machine (:24–32); `packages/workflow-harness/src/run-harness-agent-time-slice.ts` — 750s default (:8–12).
**Signature:** `runHarnessAgent({agent, state, timeSliceSeconds?, destroyOnFinish?, writable?}): Promise<HarnessWorkflowState>` — the body of a consumer's `'use step'`; the returned state IS the durable checkpoint.
**Data Shape:** `HarnessWorkflowState` = {sessionId (stable across processes; doubles as sandbox name), prompt (sent once on the execution that starts the turn), messages? (approval-resume payload), status, resumeFrom? (warm session for the NEXT user turn), continueFrom? (suspended turn of THIS run), streamContext? (open text/reasoning parts + pending tool inputs), finalResult?, error?}. Every field JSON-serializable.

### Decisive source
```ts
// run-harness-agent.ts:155–161 — the time slice races the turn; the unref'd
// timer fires suspendTurn() at the budget (default 750s: Fluid Compute recycles
// instances at ~800s, leaving a safety buffer to reattach to the live sandbox)
const timer = options.timeSliceSeconds == null ? undefined : setTimeout(() => {
  suspendPromise = session.suspendTurn();
}, options.timeSliceSeconds * 1000);
(timer as { unref?: () => void } | undefined)?.unref?.();
```
```ts
// run-harness-agent.ts:183–197 (abridged) — stream coherence across executions
if (value.type === 'start' && state.continueFrom != null) continue; // one assistant message per user turn
if (value.type === 'finish') continue;                              // intermediate finishes dropped; ONE terminal finish written by the engine
if (value.type === 'error') {
  if (suspendPromise != null && isAbortError(errorText)) continue;  // abort is the EXPECTED consequence of a suspend
  sawError = true;                                                  // anything else fails the execution, even mid-suspend
}
```

**Flow:** createSession with continueFrom > resumeFrom > fresh (the two cursors are independent: resumeFrom reattaches a warm session before starting this run's new user turn; continueFrom continues THIS run's suspended turn without resending prompt) → stream via `stream({messages})` for approval resumes, `continueStream()` for continued slices, else `stream({prompt})` → pump UI-message chunks: drop `start` on continued slices, drop intermediate `finish`, re-emit missing part-start preludes from the persisted streamContext (writeRequiredPrelude), record open parts/pending tool inputs as the stream advances → at end: error ⇒ failed (suspend's abort already filtered); suspend fired ⇒ close open parts + return ready_for_next_step with the cursor; unfinished turn with NO pending host input ⇒ ready_for_next_step; unfinished WITH pending host input ⇒ write finish + CLOSE writable + awaiting_tool_approval with finalResult and `toResumeState` (embeds continueFrom inside the resume-session data so the next user turn can also carry it); finished ⇒ write the single terminal finish + CLOSE writable + detach() (park warm) unless destroyOnFinish.
**Invariant:** the workflow output writable is closed ONLY on finished and awaiting_tool_approval — the DevKit marks the run stream done only on close, and ready_for_next_step/failed must NOT close (another execution keeps writing / the failure propagates); each pending tool input appears exactly once across slice boundaries (persisted in streamContext until its output/denial/error chunk clears it); an abort-class error during an in-flight suspend is the only error that may be swallowed; the deprecated `runHarnessAgentSlice` maps ready_for_next_step → timed_out for legacy consumers.
**Probe:** `packages/workflow-harness/src/run-harness-agent-slice.test.ts` :142–198 (first turn: one terminal finish, session kept warm), :199–222 (destroyOnFinish drops resume state), :223–276 (approval pause suspends, closes the response stream, carries both cursors), :314–352 (time slice: suspend at budget, NO destroy, NO close, cursor carried), :353–391 (continued slice uses continueStream, drops the opening start), :392–484 (continued slice reopens active parts from streamContext and preserves aggregate usage), :485–575 (pending tool input emitted exactly once across the boundary), :617–696 (semantic-step wrapper: stopWhen boundary → ready_for_next_step).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "runHarnessAgent HarnessWorkflowState streamContext writeRequiredPrelude hasPendingHostInput", limit: 10 });
```

## Verdict
Adopt the two-cursor state shape (resumeFrom vs continueFrom), the single-terminal-finish + prelude-replay stream discipline, and the close-only-on-terminal writable rule for any durable-workflow integration of a long-running agent; adapt the time-slice default to your host's instance-recycle period; omit the legacy timed_out mapping in new code. Coverage caveat: none — every branch above is test-pinned in run-harness-agent-slice.test.ts.
