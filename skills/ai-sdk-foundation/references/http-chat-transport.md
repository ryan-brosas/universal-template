<!-- capsule-v2 -->
# HTTP chat transport — how does the wire layer resolve async options, merge header layers, and answer "is there a stream to resume?"

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What does the abstract HTTP transport own versus subclasses, and what are the reconnect semantics a server must implement?

## HttpChatTransport
**Path/Symbol:** `packages/ai/src/ui/http-chat-transport.ts:HttpChatTransport` (:116-274); `DefaultChatTransport` (`packages/ai/src/ui/default-chat-transport.ts`, 36L — supplies processResponseStream via UI-message SSE decode).
**Signature:** `sendMessages({chatId, messages, trigger, messageId, abortSignal, headers?, body?, metadata?})` → POST; `reconnectToStream({chatId, ...})` → GET, returns `ReadableStream<UIMessageChunk> | null`; abstract `processResponseStream(body)`.
**Data Shape:** init options `{api='/api/chat', credentials?, headers?, body?, fetch?, prepareSendMessagesRequest?, prepareReconnectToStreamRequest?}` — headers/body/credentials are `Resolvable` (value | fn | async fn).

### Decisive source
```ts
// resolve at REQUEST time (async fns = dynamic auth tokens), call-site wins:
const baseHeaders = { ...normalizeHeaders(resolvedHeaders), ...normalizeHeaders(options.headers) };
// prepare hook REPLACES the default body wholesale when it returns one:
const body = preparedRequest?.body !== undefined ? preparedRequest.body
  : { ...resolvedBody, ...options.body, id: options.chatId, messages: options.messages,
      trigger: options.trigger, messageId: options.messageId };
// avoid caching globalThis.fetch in case it is patched by other libraries
const fetch = this.fetch ?? globalThis.fetch;
// reconnect: 204 IS the protocol for "nothing to resume":
const response = await fetch(api /* `${this.api}/${options.chatId}/stream` */, { method:'GET', ... });
if (response.status === 204) return null; // no active stream found, so we do not resume
```

**Flow:** sendMessages resolves Resolvables in order body→headers→credentials → merges init headers UNDER call-site headers → optional prepare hook may override api/headers/body/credentials → POST JSON with Content-Type first → !ok throws `Error(await response.text())` (server error text becomes the client-visible message) → empty body throws → subclass decodes. Reconnect mirrors resolution, GETs `<api>/<chatId>/stream`, treats ONLY 204 as null (other non-ok throw), and hands the resumed byte stream to the same decoder.
**Invariant:** the transport NEVER caches a fetch reference at construction — patched fetches (test harnesses, interceptors) must be observed per call. The prepare hook is REPLACE-not-merge for body/headers: returning a value discards the defaults entirely. Resume-null must be distinguishable from resume-failure (204 vs thrown error) because chat.ts turns them into ready vs error.
**Probe:** `packages/ai/src/ui/http-chat-transport.test.ts:27/:74` (default + function body), `:123/:153` (header layers), `:185` (abort signal passthrough), `:193` (mocked 204 ⇒ null).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "HttpChatTransport reconnectToStream sendMessages DefaultChatTransport", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt request-time Resolvable resolution, call-site-over-init header precedence, replace-semantics prepare hooks, per-call fetch lookup, and 204-as-null resume contract. Adapt the URL layout and body schema to your backend. Omit nothing behavioral.
