<!-- capsule-v2 -->
# useCompletion — what remains when the chat plane generalizes down to plain text?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the minimal completion hook contract and which legacy transport does it still ride on?

## useCompletion
**Path/Symbol:** `packages/ai/src/ui/use-completion.ts:useCompletion` (221L; re-exported through `packages/react/src/use-completion.ts`).
**Signature:** `useCompletion({api, id?, headers?, body?, credentials?, fetch?, streamProtocol?, onResponse?, onFinish?, onError?}): {completion, complete(input, options?), error, isLoading, stop, setCompletion}`.
**Data Shape:** `completion` accumulates streamed text; request/response go through the LEGACY shared helper `packages/ai/src/ui/call-completion-api.ts:callCompletionApi` (:1-157) — NOT the ChatTransport plane.

### Decisive source
```ts
// call-completion-api.ts: POST → hand response to caller hook → stream decode
// via consumeStream-style pump into onSuccess callbacks per delta:
const response = await fetched(api, { method: 'POST', body: JSON.stringify({...}), ... });
if (!response.ok) throw new Error((await response.text()) ?? 'Failed to fetch the response.');
// text/event-stream vs plain text decoding selected by streamProtocol;
// abort keeps partial text (stop() does not clear completion).
```

**Flow:** complete(input) → isLoading true → callCompletionApi POSTs `{prompt: input, ...body}` → onResponse interceptor may consume/return-not-ok → protocol decoder (SSE data-lines or raw text) appends deltas → onFinish(full completion) → errors land in onError + state. stop() aborts while retaining accumulated text.
**Invariant:** this is the pre-UIMessage surface kept for compatibility — new ports should target the chat plane (`chat-request-lifecycle`, `http-chat-transport`); its value here is the minimal shape of a streaming-text hook and the shared legacy API contract.
**Probe:** `packages/react/src/use-completion.ui.test.tsx` (render/stream/error lifecycle); type-level `use-completion.test-d.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "useCompletion callCompletionApi streamProtocol", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the hook contract shape if you need a bare text-streaming primitive; otherwise OMIT in favor of the chat-plane capsules (legacy product surface, documented for completeness).
