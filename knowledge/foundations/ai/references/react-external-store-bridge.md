<!-- capsule-v2 -->
# React external-store bridge — how does a mutable class store feed useSyncExternalStore without stale closures or tearing?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do I bind a long-lived imperative Chat instance into React so option callbacks never go stale and terminal status never outruns the messages it describes?

## useChat + ReactChatState
**Path/Symbol:** `packages/react/src/use-chat.ts:useChat` (:65-257); `packages/react/src/chat.react.ts:ReactChatState` (:27-149), `Chat` (:151-173).
**Signature:** `useChat(options): UseChatHelpers` — options either `{chat}` or full `ChatInit`; internals `latestRef` (:77-100), stable wrapper objects (:109-122), `useSyncExternalStore(subscribeToMessages, getMessagesSnapshot)` (:184-188).
**Data Shape:** `messagesSnapshotRef = {chat, messages}` — the snapshot PAIRS instance and array so switching chats cannot leak the old instance's messages.

### Decisive source
```ts
// keep latest values in a ref refreshed on EVERY render, hand Chat stable
// wrappers that read from it (Chat is created once — plain options would
// freeze the FIRST render's callbacks forever):
latestRef.current = { onToolCall: options.onToolCall, onData: ..., onFinish: ..., onError: ..., sendAutomaticallyWhen: ..., transport: options.transport };
const chatOptions = { ...options,
  transport: { sendMessages: o => getTransport().sendMessages(o),
               reconnectToStream: o => getTransport().reconnectToStream(o) },
  onToolCall: arg => latestRef.current.onToolCall?.(arg), /* ...same for onData/onFinish/onError */
  sendAutomaticallyWhen: arg => latestRef.current.sendAutomaticallyWhen?.(arg) ?? false };
// status subscription MUST publish messages before a terminal status can render:
if (chat.status === 'ready' || chat.status === 'error') {
  // Publish the latest messages before the terminal status can render.
  messagesSnapshotRef.current = { chat, messages: chat.messages };
}
```

**Flow:** Chat created ONCE in a ref (recreated only when injected `chat` identity differs or explicit `id` changes :128-136) → every render refreshes `latestRef.current`; the transport/callback wrappers are stable identities reading through it → `subscribeToMessages` registers a throttled callback (throttle wrapper returns identity fn when waitMs nullish — `packages/react/src/throttle.ts:3-8`), snapshots `{chat, messages}`, and RESYNCS after subscribing because `useSyncExternalStore` re-reads the snapshot post-subscribe and a change between render and subscribe would otherwise be missed (:166-169) → message arrays are replaced IMMUTABLY by the store (`concat`/`slice`/spread — `chat.react.ts:69-86`) so identity change IS the notification; `snapshot()` shallow-copies each message's `parts` array and `cloneMetadata`s plain objects before replacement so consumers never mutate in-flight parts → status subscriber additionally flushes messages BEFORE emitting terminal `ready`/`error` → `setMessages` accepts updater fn evaluated against CURRENT store messages.
**Invariant:** the pairing `(chat, messages)` in one ref object is the tear-guard — a porter storing bare `messages` renders the new array against the old chat instance after an id swap; a porter freezing callbacks at mount makes every user callback permanently stale; a porter mutating arrays in place never triggers subscribers.
**Probe:** `packages/react/src/chat.react.test.ts` (store semantics), `packages/react/src/use-chat.ui.test.tsx` (hook round-trip incl. throttle + resume).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "useChat ReactChatState registerMessagesCallback useSyncExternalStore", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the latestRef/stable-wrapper pattern, the paired snapshot ref, the post-subscribe resync, and the terminal-status-flushes-messages ordering. Adapt store mutators to your domain. Omit the deprecated alias surface (`addToolResult`). Direct tests exist; no coverage caveat.
