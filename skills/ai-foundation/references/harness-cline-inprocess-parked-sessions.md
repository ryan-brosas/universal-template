<!-- capsule-v2 -->
# Cline in-process parked sessions — how do you keep a live turn alive across detach/suspend when the runtime runs in the host process with no bridge?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** When a dialect runtime is an in-process Node library (no attachable bridge, no replayable event log), which lifecycle methods can still continue a live turn, and what must degrade to lossy rerun?

## The parked-session continuation split
**Path/Symbol:** `packages/harness-cline/src/cline-session.ts` — `parkedClineSessions` (:81), `doDetach` (:875–895), `doSuspendTurn` (:897–963), resume pop (:244–249), silent-suspend guard (:731), steering loop (:642–665).
**Signature:** `createClineSession(input): Promise<HarnessV1Session>` where the session's `doDetach`/`doSuspendTurn` return `{type:'resume-session'|'continue-turn', data:{historyFileName}}`.
**Data Shape:** module-level `Map<string, HarnessV1Session>` keyed by sessionId; per-session pending maps (`pendingToolResults`, `pendingToolApprovals`) and a `suspending` flag; the sandbox private dir holds only the serialized conversation history (`history.json` under `<sandboxHome>/.ai-sdk/harness-cline/<sha256(sessionId)>`).

### Decisive source
```ts
// cline-session.ts:875–895 — detach parks the LIVE session when host input is pending
doDetach: async (): Promise<HarnessV1ResumeSessionState> => {
  if (activeTurn != null || pendingToolResults.size > 0) {
    parkedClineSessions.set(input.sessionId, sessionImpl);
    try {
      await persistHistory();
    } catch {
      /*
       * The parked in-process session is the authoritative continuation
       * path while the live turn is waiting on host input. Persistence
       * is only a fallback for later non-live resumes.
       */
    }
    return { type: 'resume-session', ... data: { historyFileName: CLINE_DEFAULT_HISTORY_FILE_NAME } };
  }
  return doStop();
},
```
```ts
// cline-session.ts:933–940 — suspend WITHOUT pending input aborts the turn silently
suspending = true;
agent?.abort('Cline session suspended');
if (activeTurn) {
  await activeTurn.done.catch(() => {});
}
// ...persist history best-effort, teardown...
// cline-session.ts:731 — the turn's catch swallows ONLY its own abort
if (suspending && isAbortError(error)) return;
currentEmit?.({ type: 'error', error });
```

**Flow:** doStart with isResume first checks the parked map and returns the live session if present (:244–249) → doDetach/doSuspendTurn with pending host input park the session object (turn stays blocked on its parked promise) and persist history as fallback → without pending input, suspend sets `suspending`, aborts the agent, awaits the turn's silent settle, persists, tears down → the next process pulls `history.json` from the sandbox and rerun-continues (`runtime.continue()` with no input re-drives from the restored transcript — `text === undefined` means "continue", never an empty user message, :643–651) → mid-turn steering rides `consumePendingUserMessage()` between loop iterations (:662–668); queued messages are rejected when the turn ends without consuming them.
**Invariant:** a same-process resume NEVER loses a live turn (parked session wins over the persisted copy); a cross-process resume is ALWAYS lossy rerun (the in-flight tail is recomputed — a host-resident runtime cannot freeze a turn the way a bridge adapter can); the `suspending` guard swallows only abort-class errors, so an unanticipated failure mid-suspend still surfaces as an `error` chunk; structured output is a `structured_output` completion tool (`completesRun` + `requireCompletionTool`) whose result is re-emitted as a synthetic text block + zero-usage finish-step, and json-without-schema / openai-codex-cli provider are rejected up front.
**Probe:** `packages/harness-cline/src/cline-session.test.ts` :218–236 ("applies instructions when rerunning a suspended turn" — pins `continueInputs [undefined]`, i.e. rerun-continue sends no user message), :256–281 (steering consumed between iterations; late steering rejects 'no running turn'), :283–310 (queued steering rejected when the turn fails first), :733–800 (structured_output tool schema + requireCompletionTool + synthetic text-delta), :802+ (codex-cli structured-output rejection). Caveat: NO direct test pins doDetach/doSuspendTurn/parkedClineSessions behavior — the park path is deterministic-read-only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "parkedClineSessions doSuspendTurn suspending consumePendingUserMessage structured_output", limit: 10 });
```

## Verdict
Adopt the two-tier continuation model (live-parked map for same-process, persisted-state rerun for cross-process) and the silent-suspend abort filter for any in-process dialect; adapt the persisted state shape (cline stores a messages JSON; pi stores its journal file — see the pi capsules); omit the bridge machinery entirely (no SandboxChannel, no replay log, no disk-log classify). Caveat: park/detach/suspend paths have no dedicated test coverage in this package.
