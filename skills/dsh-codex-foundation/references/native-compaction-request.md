<!-- capsule-v2 -->
# Native compaction request — shape, authenticate, observe, and fall back when the Codex V2 endpoint refuses compaction

**Source:** dsh-codex Apache-2.0 main@e3e54e206f7c829503c7e6eed378643ba0416792; Codebase Memory dsh-codex. **Question:** how do you compose the native compaction HTTP request (body, auth, session headers) and guarantee compaction still happens when the experiment fails?

## OpenAICodexResponseRuntime.requestNativeCompaction / nativeCompactionStream (+ retainedCompactionInput, accountIdFromToken)
**Path/Symbol:** src/responses.ts:407-499 (request), 385-405 (stream/fallback), 318-322 (retained filter), 83-96 (JWT account id); URL constant 23.
**Signature:** private async requestNativeCompaction(model, context, options?): Promise<CompactResponse>; private nativeCompactionStream(provider, model, context, options?): AssistantMessageEventStream; retainedCompactionInput(input: readonly unknown[]): unknown[].
**Data Shape:** POST https://chatgpt.com/backend-api/codex/responses with body {model, store:false, stream:true, input:[...expandedHistory, {type:'compaction_trigger'}], instructions, tools?, tool_choice:'auto', parallel_tool_calls:true, include:['reasoning.encrypted_content'], reasoning?{effort,summary}, prompt_cache_key?, text:{verbosity:'low'}}; headers Bearer access + chatgpt-account-id (from JWT payload auth claim chatgpt_account_id) + originator + accept text/event-stream + openai-beta responses=experimental + session-id/thread-id/x-client-request-id + x-codex-routing-hint model=<id>.

### Decisive source
~~~ts
const messages = context.messages.length === 0 ? [] : context.messages.slice(0, -1)
const input = expandNativeCompactionMarkers(convertResponsesMessages(
  model, { ...context, messages }, CODEX_TOOL_CALL_PROVIDERS, { includeSystemPrompt: false }))
…
const retained = retainedCompactionInput(input)   // keeps role user/developer/system items only
let body = { …, input: [...input, { type: 'compaction_trigger' }], store: false, stream: true, … }
if (options?.onPayload !== undefined) { body = await options.onPayload(body, model) ?? body }
…
headers.set('authorization', 'Bearer ' + access)
headers.set('chatgpt-account-id', accountIdFromToken(access))
headers.set('originator', 'dsh-codex')
… session-id/thread-id/x-client-request-id when sessionId present; x-codex-routing-hint model=<id>

// fallback (nativeCompactionStream):
error => {
  const source = options?.signal?.aborted === true
    ? failedStream(model, error, options.signal)
    : this.standardStream(provider, model, context, options, false)
  void (async () => { for await (const event of source) target.push(event) })()
}
~~~

**Flow:** require OAuth token → drop the trailing (compaction-instruction) message → convert history without system prompt, expanding prior markers → retain user/developer/system items → append compaction_trigger → let onPayload rewrite the body → set auth/account/session/routing headers → POST with retries (see compaction-retry-ladder) → parse SSE (see compaction-sse-parse) → emit the framed checkpoint as a synthetic assistant text stream; any non-abort failure reruns the standard stream so Harness compaction still produces a summary, while an aborted call emits stopReason 'aborted'.
**Invariant:** the trigger item exists exactly once and only in the experimental body; history conversion excludes the system prompt and prior markers are expanded before sending; retained output preserves Codex's durable-history shape (client messages + opaque item); onResponse observes every attempt status+headers; fallback never runs after abort; the account id derivation fails with a sign-in-again message instead of sending a malformed header; the marker stream pushes start/text*/done events inside a microtask with real usage attached.
**Probe:** tests/codex-compaction.spec.ts:221-322 (checkpoint + restore round trip, thread-id/x-codex-routing-hint/body pinned) and 324-387 (HTTP 400 → standard-stream fallback summary); executed via pnpm test -- tests/codex-compaction.spec.ts.

## Get live surrounding code
**Retrieve:**
~~~ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.responses\\.(OpenAICodexResponseRuntime\\.requestNativeCompaction|retainedCompactionInput|accountIdFromToken)', limit: 10, fields: ['signature', 'name', 'file', 'lines'] });
~~~

## Verdict
Adopt the strip-last-message + expand-markers + retained-filter + trigger-item composition and the guarantee that compaction degrades to the standard path rather than failing the session. Adapt endpoint, headers, trigger vocabulary, and JWT claim paths (search-provider.md documents the search-plane twin of accountIdFromToken — same pattern, separate module). Omit first-party originator/beta header values. Coverage no_recorded_issue + metadata_match for src/responses.ts and tests/codex-compaction.spec.ts.
