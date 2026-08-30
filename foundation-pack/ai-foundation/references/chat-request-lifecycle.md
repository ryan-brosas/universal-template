<!-- capsule-v2 -->
# Chat request lifecycle — how does AbstractChat serialize concurrent mutations, resume streams, and keep onFinish total?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** Where must a porter place locks, abort wiring, and terminal callbacks so tool outputs, auto-resubmits, and stream resumes never interleave corruptly?

## AbstractChat
**Path/Symbol:** `packages/ai/src/ui/chat.ts:AbstractChat` (:242-886) — framework-agnostic; the React `Chat` is only a state shell.
**Signature:** `sendMessage(message?, options?)` / `regenerate({messageId}?)` / `resumeStream(options?)` / `stop()` / `addToolOutput({toolCallId, output|errorText})` / `addToolApprovalResponse({id, approved})`; private `makeRequest({trigger, ...})` (:628-885).
**Data Shape:** three concurrency primitives: `pendingMessagePreparations: Set<AbortController>` (file→part conversion can be slow), `activeResponse` (the one streaming response), `activeResumeRequest` (resume-only, with `isCurrentRequest()` staleness gate); ONE shared `SerialJobExecutor jobExecutor`.

### Decisive source
```ts
// every stream chunk AND every addToolOutput/addToolApprovalResponse runs here —
// serialized to avoid race conditions:
this.jobExecutor.run(async () => { /* mutate parts / apply chunk */ });
// resume-stream checks for an active stream BEFORE changing status:
if (trigger === 'resume-stream') {
  const reconnect = await this.transport.reconnectToStream({...});
  if (reconnect == null) { this.setStatus({status:'ready'}); return; } // avoids a brief flash of 'submitted' on page load
  if (response.status === 204) return null; // transport side: no active stream ⇒ resume silently no-ops
}
// stop() fans out in dependency order:
for (const c of this.pendingMessagePreparations) c.abort();
this.activeResumeRequest?.abortController.abort();
this.activeResponse?.abortController.abort();
// onFinish fires in nested finally — even when the callback itself throws,
// cleanup still runs:
try { if (activeResponse) this.onFinish?.({message, messages, isAbort, isDisconnect, isError, finishReason}); }
finally { if (this.activeResponse === activeResponse) this.activeResponse = undefined;
         clearActiveResumeRequest(); }
```

**Flow:** sendMessage prepares files under a tracked AbortController (`signal.aborted` checked AFTER await → silently return :387-389), trims history on `messageId` replace (slice through index + replaceMessage) or pushes new user message → makeRequest: resume requests supersede predecessors and everything downstream re-checks `isCurrentRequest()` before touching status → status `submitted` → transport.sendMessages → each UIMessageChunk processed via `runUpdateMessageJob` = jobExecutor.run (aborted-signal short-circuit inside) whose `write()` flips status to `streaming`, then replaces last message by id match or pushes → consumeStream; abort ⇒ ready (NOT error); TypeError containing 'fetch'/'network' classifies `isDisconnect` (:841-847); other errors ⇒ onError + status error → finally fires onFinish ALWAYS → post-success `shouldSendAutomatically()` may chain another submit-message. Tool-part updates write BOTH stores: committed message via replaceMessage AND `activeResponse.state.message.parts` in place (:526-529, :574-579).
**Invariant:** all state mutation funnels through the SerialJobExecutor — a porter applying chunks or tool outputs outside it reintroduces the exact races it exists to kill (auto-send deadlock note: `shouldSendAutomatically().then(...)` deliberately UN-awaited inside jobExecutor jobs :537-546). Resume-before-status preserves UI truth on page load. onFinish is total.
**Probe:** `packages/ai/src/ui/chat.test.ts:998` ("should stop updating messages when a resumed stream is stopped"), `:1061` (stop while reconnection pending), `:1111` (only latest overlapping resumed stream applies), `:800`/:804 (abort ⇒ onFinish still called).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "AbstractChat makeRequest resumeStream sendAutomaticallyWhen", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the executor-serialization, the resume-staleness gate (`isCurrentRequest`), the 204-means-nothing-to-resume contract, stop() fan-out order, and nested-finally onFinish. Adapt trigger names/disconnect heuristics to your wire protocol. Omit nothing behavioral.
