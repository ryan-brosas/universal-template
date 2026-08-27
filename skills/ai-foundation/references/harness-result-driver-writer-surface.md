<!-- capsule-v2 -->
# Harness result writer surface — which pushed parts become step content, which stay continuation-only, and when does replayed content get discarded?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** Your driver pushes approval responses and out-of-band tool results BETWEEN model calls — how do you keep them visible on the stream without corrupting per-step `StepResult`s?

## Three-method writer: enqueue / enqueueContinuation / discardCurrentStepContent

**Path/Symbol:** `packages/harness/src/agent/internal/harness-stream-text-result.ts` — `enqueue` (:221–225), `enqueueContinuation` (:232–234), `discardCurrentStepContent` (:240–244), `startStep` (:318–327), `appendToCurrentStepContent` (:810–841); drive sites `run-prompt.ts` :403–479 (approval responses + host tool outcomes ride enqueueContinuation), :669–674 (resumed-step close), :1025–1034 (timed-slice discard).
**Signature:** `enqueue(part)` vs `enqueueContinuation(part)` vs `discardCurrentStepContent()`; `private startStep(): void`; `private appendToCurrentStepContent(part): void`.
**Data Shape:** `currentStepContent: ContentPart[]`, `currentStepWarnings`, `stepStarted` latch; continuation parts are forwarded to the controller only.

### Decisive source
```ts
// :221–225 — normal parts BOTH stream and accumulate into the open step
enqueue(part) {
  this.startStep();                       // lazily emits {type:'start-step'} once
  this.fullStreamController.enqueue(part);
  this.appendToCurrentStepContent(part);
}
// :227–234 — continuation input is NOT attributed to the next model step
// "Approval responses and client tool results arrive between model calls and
//  therefore must not create or alter a StepResult."
enqueueContinuation(part) {
  this.fullStreamController.enqueue(part);
}
// :240–244 — a suspended host-input pause closes its ALREADY-recorded model step;
// content the runtime replays across resume must not double-count
discardCurrentStepContent() {
  this.currentStepContent = []; this.currentStepWarnings = []; this.stepStarted = false;
}
// :812–825 — contiguous same-id text-deltas coalesce into ONE text part (mutating append)
case 'text-delta': {
  const last = this.currentStepContent[this.currentStepContent.length - 1];
  if (last && last.type === 'text') { (last as { text: string }).text += part.text; }
  else { this.currentStepContent.push({ type: 'text', text: part.text }); }
```

**Flow:** model-call events → `enqueue` (step-attributed, start-step synthesized); inter-call events (tool-approval-response, tool-result, tool-error from host execution) → `enqueueContinuation` (stream-only); a resumed turn's closing `finish-step` for an already-recorded step, or a timed slice ending mid-step with no finish-step yet, → `discardCurrentStepContent` so replay/slice-tail content cannot fabricate or duplicate a StepResult.
**Invariant:** StepResults contain ONLY in-step content; stream visibility never implies history attribution; discard resets the stepStarted latch so the NEXT real step re-opens cleanly; text-delta coalescing keys on adjacency+same-id only.
**Probe:** deterministic content probes at pin: run-prompt.ts :407/:464/:474 all three continuation sites call `result.enqueueContinuation` (read-verified); direct tests `run-prompt.test.ts:670–701` ("fails a mid-stream that closes without an intentional suspension" — proves discard is suspension-gated, not unconditional) and `run-prompt.test.ts:733–752` ("allows an empty terminal turn without recording a step" — steps=[]).
**Retrieve:** `search_graph { project:"ai", query:"discard current step content suspension replay", limit:3 }` → rank#1 `HarnessStreamTextResult.discardCurrentStepContent :240–244`, rank#2 bridge `replay :538–544`, rank#3 `appendToCurrentStepContent :810–841` (verified live @pin).

## Get live surrounding code
```ts
await mcp.codebase_memory.get_code_snippet({ project: "ai", qualified_name: "ai.packages.harness.src.agent.internal.harness-stream-text-result.HarnessStreamTextResult.enqueueContinuation" });
await mcp.codebase_memory.trace_path({ project: "ai", function_name: "ai.packages.harness.src.agent.internal.run-prompt.runPrompt", direction: "inbound" });
```

## Verdict
Adopt the split writer surface (step-attributed vs continuation-only vs discard) for any event-driven fake of step-based results; adapt part-type membership to your union; omit discard if your runtime cannot pause/resume mid-turn.
