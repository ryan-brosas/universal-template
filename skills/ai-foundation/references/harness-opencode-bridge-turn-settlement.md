<!-- capsule-v2 -->
# OpenCode bridge turn settlement — how do you settle a turn against an event stream that can end early, while steering messages keep arriving, without fabricating a response?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** When the sandboxed runtime reports progress through an SSE event stream that may close before the turn finishes, and mid-turn user messages keep arriving on a separate rail, what decides that the turn is over — and what must be true before it may end?

## One deferred, two settlers, a steering gate
**Path/Symbol:** `packages/harness-opencode/src/bridge/index.ts` — `runPrompt` (:556–761), `createDeferred` (:1364–1373), `consumeEvents` (:855–925), `legacyStatusType` (:498–503).
**Signature:** `runPrompt({client, sessionId, start, turn, emit}): Promise<HarnessUsage | undefined>`; internal `turnSettled = createDeferred<'event' | 'stream-ended'>()`.
**Data Shape:** flags `sawContent`, `sawFinishStep`, `sawBusy`, `sawStructuredOutput`, `terminalError`, `submittingUserMessage`; `state = createTranslationState()`; `initialSessionTokens` read BEFORE the prompt (`.catch(() => undefined)`); `assistantBaseline` captured from the latest assistant snapshot; `eventsReady` deferred resolved by subscription (and by the loop's `.finally`).

### Decisive source
```ts
// index.ts:663–680 — busy→idle is only a SETTLEMENT CANDIDATE; steering and
// structured output gate it
const status = legacyStatusType(event);
if (status === 'busy') {
  sawBusy = true;
} else if (status === 'retry') {
  sawBusy = true;
  turn.emitWarning({ message: legacyRetryStatusMessage(event) });
} else if (sawBusy && status === 'idle') {
  sawBusy = false;
  if (
    !submittingUserMessage &&
    turn.experimental_userMessages.pendingCount === 0 &&
    (start.responseFormat?.type !== 'json' || sawStructuredOutput)
  ) {
    turn.experimental_userMessages.close();
    turnSettled.resolve('event');
    return true;
  }
}
```
```ts
// index.ts:726–748 — post-settlement ladder: stream-ended and terminal errors
// throw; a settled-but-uncorrelated turn falls back to the runtime's own store
const settlement = await turnSettled.promise;
eventsAbort.abort();
await eventLoop.catch(() => {});
await userMessageLoop.catch(() => {});
if (settlement === 'stream-ended') {
  throw new Error('OpenCode event stream ended before the turn settled.');
}
if (terminalError) throw new Error(terminalError);
if (!sawFinishStep) {
  const emittedFallback = await emitContextFallback({ ... }).catch(() => false);
  if (!emittedFallback) {
    throw new Error(
      'OpenCode turn settled without a correlated assistant response.',
    );
  }
}
```

**Flow:** subscribe to events FIRST (`await eventsReady.promise`) so no early event is lost → start the steering loop (`for await (message of turn.experimental_userMessages)`; each message re-prompts via `legacySessionPrompt`, `accept()`/`reject()` per message, `submittingUserMessage` set around the await) → send the initial prompt → wait on `turnSettled`. Settlers: (a) `message.updated` carrying `info.structured` under json responseFormat emits text-start/delta(JSON.stringify)/end + finish-step and settles when nothing is pending; (b) `session.error`/`session.next.step.failed` closes the user-message rail WITH the error and settles; (c) busy→idle settles when ungated; (d) the loop's `.finally` settles `'stream-ended'` and rejects the rail. After settlement: abort the event stream, drain both loops swallowing their rejections, then run the throw ladder above. Usage returns the session-token delta (see usage-accounting capsule) or the accumulated `stepUsage`.
**Invariant:** the turn settles EXACTLY ONCE (a plain resolve-once deferred makes double-settlement impossible); a consumer never receives a turn that ended without either a correlated assistant response (streamed or fallback-emitted) or an explicit error; a queued or in-flight steering message can never be orphaned by an idle transition.
**Probe:** `packages/harness-opencode/src/bridge/index.test.ts` (138L, 1 case): a mocked SDK whose event stream yields one `session.next.step.failed` drives the real module entry — asserts the user-message rail closed with the error object, `emitError` got 'OpenCode turn failed', and the LAST emitted part is `{type:'finish'}` (the runTurn finally-block terminal).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "runPrompt turnSettled consumeEvents legacyStatusType experimental_userMessages", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-deferred dual-settler shape (event-side settlers + stream-ended fallback) for any turn driven by a push stream that may die early; adopt the steering gate (settle only when no message is submitting AND none pending) whenever a mid-turn user-message rail exists; adopt the post-settlement throw ladder (stream-ended ⇒ error, terminal error ⇒ error, uncorrelated ⇒ recovery-or-error) as the total boundary. Adapt the status vocabulary (busy/retry/idle) and the structured-output short-circuit to your runtime's signals; omit the legacy SDK duck-typing shims unless you support multiple client versions. Caveat: only ONE test drives the full path (the step.failed case); the idle-settlement, structured-output, and steering gates are deterministic-read-only.
