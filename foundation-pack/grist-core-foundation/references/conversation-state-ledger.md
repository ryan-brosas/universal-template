<!-- capsule-v2 -->
# Conversation state ledger & telemetry indices — who owns chat history between assistant turns, and what exactly gets logged?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How does stateless server + stateful client conversation work, and which message indices are emitted to telemetry?

## Response returns full messages array; client echoes it back next turn; assistantSend/Receive log absolute indices
**Path/Symbol:** `app/common/Assistance.ts`: `AssistanceState {messages?}` (:14–16), role union incl. `"tool"` (:18–22), V1/V2 discrimination via `!("tableId" in req.context)` (:41–43); `OpenAIAssistantV1.getAssistance` push points (:93–120), index logging (:122–136), completion append (:142), receive log (:163–174).
**Signature:** `state: { messages?: AssistanceMessage[] }` round-trips untouched except appends.
**Data Shape:** Message `{role, content?, tool_call_id?}` — OpenAI wire shape verbatim.

### Decisive source
```ts
const messages = request.state?.messages || [];
const newMessages: AssistanceMessage[] = [];
if (messages.length === 0) newMessages.push(await generatePrompt());   // lazy system prompt
...
newMessages.push({ role: "user", content: request.text });
messages.push(...newMessages);
const newMessagesStartIndex = messages.length - newMessages.length;
for (const [index, { role, content }] of newMessages.entries()) {
  doc.logTelemetryEvent(optSession, "assistantSend", {
    full: { version: 1, conversationId: request.conversationId,
            prompt: { index: newMessagesStartIndex + index, role, content } },
  });
}
const completion = await this._getCompletion(messages, {...});
messages.push({ role: "assistant", content: completion });
response.state = { messages };
```

**Flow:** server keeps NO conversation store: each request carries prior history, server appends its new turns and returns the WHOLE array for the client to persist (doc comment: client shouldn't parse it — format stability deliberately uncommitted). Telemetry records only the DELTA but with ABSOLUTE indices (`newMessagesStartIndex`) so server-side logs can be replayed into one transcript; assistantReceive logs final index `messages.length - 1` plus suggestedFormula.
**Invariant:** The evaluateCurrentFormula system message (:98–115) is injected AFTER the schema prompt and BEFORE the user text every time evaluation is requested — position carries meaning for the model. History mutation happens on a LOCAL array then gets returned; mutating request.state in place would alias caller memory across retries. A porter storing history server-side breaks multi-worker routing (turn N may hit any worker).
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -n "newMessagesStartIndex" app/server/lib/OpenAIAssistantV1.ts && grep -n "role: \"system\" | \"user\" | \"assistant\" | \"tool\"" app/common/Assistance.ts'` → :122/:129; role union :19.
Direct tests: `test/server/lib/OpenAIAssistantV1.ts` :96 case asserts `state.messages` deep-equals `[...requestMessages, replyMessage]`; :312 past-history case feeds 3-message state.

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"AssistanceState messages conversationId logTelemetryEvent assistantSend","limit":5,"detail":"ids"}'
```

## Verdict
Adopt client-owned state + delta-with-absolute-indices telemetry; adapt event names to your pipeline; omit tool_call_id plumbing until you port a tool-using assistant variant.
